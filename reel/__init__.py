"""This is reel."""
# pylint: disable=R0801
from datetime import datetime
import logging
import os
import shlex
import subprocess

import pkg_resources
import trio

from . import config
from ._path import Path

__version__ = pkg_resources.get_distribution(__name__).version

# pylint: disable=W0212


class Reel:
    """A stack of spools concatenated in place as one spool in a transport."""

    def __init__(self, spools, announce_to=None):
        """Begin as a list of spools."""
        self._announce = announce_to
        self._spools = spools

    def __or__(self, the_other_one):
        """Board the __or__ train, creating `Transport` as first in chain."""
        return Transport(self, the_other_one)

    async def send(self, channel):
        """Send the spools' stdout to the send `channel`."""
        async with channel:
            for spool in self._spools:
                if self._announce:
                    self._announce(spool)
                await spool.send_to_channel(channel)
                await spool.stdout.aclose()

    async def aclose(self):
        """Close the spools."""
        for spool in self._spools:
            await spool.aclose()

    async def handle_stderr(self, nursery):
        """Read stderr, called as a task by a Transport in a nursery."""
        for spool in self._spools:
            nursery.start_soon(spool.handle_stderr, nursery)


class Spool(trio.abc.AsyncResource):
    """A command to run as an async subprocess in a ``Transport``."""

    def __init__(self, command, xenv=None, xflags=None):
        """Start a subprocess with a modified argument list and environment."""
        self._command = shlex.split(command)
        self._env = dict(os.environ)
        self._limit = None
        self._status = None
        self._stderr = None
        self._timeout = None
        if xflags:
            for flag in xflags:
                self._command.append(str(flag))  # str for error with Path...
        if xenv:
            for key, val in xenv.items():
                self._env[key] = val
        logging.debug(' '.join(self._command))

        self._proc = trio.Process(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._env
        )

    async def __aenter__(self):
        """Run through a tranport in an async managed context."""
        return Transport(self)

    async def aclose(self):
        """Wait for the process to end and close it."""
        self._proc.wait()
        await self._proc.aclose()

    @property
    def returncode(self):
        """Return the exit code of the process."""
        return self._proc.returncode

    @property
    def stderr(self):
        """Return whatever the process sent to stderr."""
        if self._stderr:
            return self._stderr.decode('utf-8')
        return None

    @property
    def stdout(self):
        """Return stdout of the subprocess."""
        return self._proc.stdout

    def limit(self, byte_limit=65536):
        """Configure this `spool` to limit output to `byte_limit` bytes."""
        self._limit = byte_limit
        return self

    def timeout(self, seconds=0.47):
        """Configure this `spool` to stop after `seconds` seconds."""
        self._timeout = seconds
        return self

    async def run(self, message=None, text=True):
        """Send stdin to process and return stdout."""
        return await Transport(self).read(message, text=text)

    def __repr__(self):
        """Represent prettily."""
        return f"Spool('{' '.join(self._command)}')"

    def __or__(self, the_other_one):
        """Create a `Transport` out of the first two spools in the chain."""
        return Transport(self, the_other_one)

    async def receive(self, channel):
        """Send the output of the receive `channel` to this spool's stdin."""
        async for chunk in channel:
            await self._proc.stdin.send_all(chunk)
        await self._proc.stdin.aclose()  # ??? unless last in chain

    async def send(self, channel):
        """Stream stdout to `channel` and close both sides."""
        logging.debug('seinding to channel!!!')
        async with channel:
            await self.send_to_channel(channel)
        await self._proc.stdout.aclose()

    async def send_to_channel(self, channel):
        """Stream stdout to `channel` without closing either side."""
        buffsize = 16384
        if self._limit and self._limit < 16384:
            buffsize = self._limit
        logging.debug('-----!!!!!!!>>>>>>>>>> %s %s', self._limit, buffsize)
        bytes_received = 0
        chunk = await self._proc.stdout.receive_some(buffsize)
        _start_time = datetime.now().microsecond
        while chunk:

            # Send data.
            await channel.send(chunk)
            bytes_received += len(chunk)

            # Check for byte limit.
            if self._limit and bytes_received > self._limit:
                break

            # Check for timeout.
            if self._timeout:
                now = datetime.now().microsecond
                if (now - _start_time) >= self._timeout * 1000:
                    break

            # Read from stdout.
            buffsize = 16384
            if self._limit and self._limit < 16384:
                buffsize = self._limit
            chunk = await self._proc.stdout.receive_some(buffsize)

    async def _handle_stderr(self):
        """Read stderr in a function so that the nursery has a function."""
        while True:
            chunk = await self._proc.stderr.receive_some(16384)
            if not chunk:
                break
            if not self._stderr:
                self._stderr = b''
            self._stderr += chunk

    async def handle_stderr(self, nursery):
        """Read stderr, called as a task by a Transport in a nursery."""
        nursery.start_soon(self._handle_stderr)


class Transport(trio.abc.AsyncResource):
    """A device for running spools."""

    def __init__(self, *args):
        """Create a transport chain from a list of spools."""
        self._nursery = None
        if len(args) == 1 and isinstance(args[0], list):
            self._chain = []
            for spool in args[0]:
                self._chain.append(spool)
        else:
            self._chain = list(args)

    def _append(self, spool):
        """Add a spool to this transport chain."""
        self._chain.append(spool)

    @property
    def stdin(self):
        """Return stdin of the first spool in the chain."""
        return self._chain[0]._proc.stdin

    async def _handle_stdin(self, message):
        """Send a message to stdin."""
        async with self.stdin as stdin:
            try:
                await stdin.send_all(message)
            except trio.BrokenResourceError:
                logging.error('trio.BrokenResourceError')

    @property
    def stdout(self):
        """Return stdout of the last spool in the chain."""
        return self._chain[-1]._proc.stdout

    async def _run(self, message=None, stdout=False):
        """Connect the spools with pipes and let the bytes flow."""
        output = None
        async with trio.open_nursery() as nursery:

            # Chain the spools with pipes.
            for idx, spool in enumerate(self._chain):
                if idx < len(self._chain) - 1:
                    _src = spool
                    _dst = self._chain[idx + 1]
                    send_ch, receive_ch = trio.open_memory_channel(0)
                    async with send_ch, receive_ch:
                        nursery.start_soon(_src.send, send_ch.clone())
                        nursery.start_soon(_dst.receive, receive_ch.clone())

            # Queue the message to stdin.
            if message:
                nursery.start_soon(self._handle_stdin, message)

            # Handle stderr streams.
            for spool in self._chain:
                nursery.start_soon(spool.handle_stderr, nursery)

            # Read stdout from the last spool in the list.
            if stdout:
                output = b''
            ch_send, ch_receive = trio.open_memory_channel(0)
            nursery.start_soon(self._chain[-1].send, ch_send)
            async for chunk in ch_receive:
                if stdout:
                    output += chunk

        # Close the subprocesses.
        for spool in self._chain:
            logging.debug('wtf?????????????????????????????????')
            await spool.aclose()

        if stdout:
            return output

    async def play(self) -> None:
        """Run this transport and ignore stdout."""
        await self._run()

    async def read(self, message=None, text=True):
        """Run transport and return stdout as str."""
        if message and text:
            message = message.encode('utf-8')
        rawbytes = await self._run(message=message, stdout=True)

        if text:
            # Remove trailing \n.
            decoded = rawbytes.decode('utf-8')
            if decoded[-1:] == '\n':
                decoded = decoded[:-1]
            return decoded
        return rawbytes

    async def readlines(self):
        """Run this transport and return stdout as a `list`."""
        output = (await self._run(stdout=True)).decode('utf-8')
        return output.split('\n')[:-1]

    def __repr__(self):
        """Represent prettily."""
        return str(self._chain)

    def __or__(self, the_other_one):
        """Store all the chained spools and reels in this transport."""
        self._append(the_other_one)
        return self

    async def aclose(self):
        """Clean up resources."""
