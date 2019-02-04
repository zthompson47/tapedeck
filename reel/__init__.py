"""This is reel."""
# pylint: disable=R0801
import logging
import os
import shlex
import subprocess

import trio

from . import config
from ._path import Path

from ._version import __version__  # noqa: F401
from .proc import Destination, Source  # noqa: F401

# pylint: disable=W0212

LOGGING_LEVEL = os.environ.get(
    'REEL_LOGGING_LEVEL',
    'debug'
).upper()
LOGGING_DIR = os.environ.get(
    'REEL_LOGGING_DIR',
    trio.run(config.get_xdg_config_dir)
)
LOGGING_FILE = os.environ.get(
    'REEL_LOGGING_FILE',
    str(Path(LOGGING_DIR) / 'reel.log')
)


class Reel:
    """A stack of spools concatenated in place as one spool in a transport."""

    def __init__(self, spools):
        """Begin as a list of spools."""
        self._spools = spools

    def __or__(self, the_other_one):
        """Board the __or__ train, creating `Transport` as first in chain."""
        return Transport(self, the_other_one)

    async def send(self, channel):
        """Send the spools' stdout to the send `channel`."""
        async with channel:
            for spool in self._spools:
                await spool.send_to_channel(channel)
                await spool.stdout.aclose()


class Spool:
    """A command to run as an async subprocess in a ``Transport``."""

    def __init__(self, command, xenv=None, xconf=None):
        """Start a subprocess with a modified argument list and environment."""
        self._command = shlex.split(command)
        self._env = dict(os.environ)
        self._limit = None
        if xconf:
            for flag in xconf:
                self._command.append(flag)
        if xenv:
            for key, val in xenv.items():
                self._env[key] = val
        logging.debug(' '.join(self._command))
        self._proc = trio.Process(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=self._env
        )

    @property
    def stdout(self):
        """Return stdout of the subprocess."""
        return self._proc.stdout

    def limit(self, byte_limit=16384):
        """Configure this `spool` to limit output to `byte_limit` bytes."""
        self._limit = byte_limit
        return self

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
        async with channel:
            await self.send_to_channel(channel)
        await self._proc.stdout.aclose()

    async def send_to_channel(self, channel):
        """Stream stdout to `channel` without closing either side."""
        buffsize = 16384
        if self._limit and self._limit < 16384:
            buffsize = self._limit
        bytes_received = 0
        chunk = await self._proc.stdout.receive_some(buffsize)
        while chunk:
            await channel.send(chunk)
            bytes_received += len(chunk)
            if self._limit and bytes_received > self._limit:
                break
            buffsize = 16384
            if self._limit and self._limit < 16384:
                buffsize = self._limit
            chunk = await self._proc.stdout.receive_some(buffsize)


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

    async def _run(self, stdin=None, stdout=False):
        """Connect the spools with pipes and let the bytes flow."""
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

            # Send a message to stdin, after the chain establishes stdin.
            if stdin:
                nursery.start_soon(self._handle_stdin, stdin)

            # Discard stdout from the last spool in the list.
            output = None
            if stdout:
                output = b''
            async with self.stdout as out:
                while True:
                    chunk = await out.receive_some(16384)
                    if chunk:
                        if stdout:
                            output += chunk
                    else:
                        break
            if stdout:
                return output

    async def play(self):
        """Run this transport and ignore stdout."""
        return await self._run()

    async def readlines(self):
        """Run this transport and return stdout as a `list`."""
        output = await self._run(stdout=True)
        return output.split(b'\n')[:-1]

    def __repr__(self):
        """Represent prettily."""
        return str(self._chain)

    def __or__(self, the_other_one):
        """Store all the chained spools and reels in this transport."""
        self._append(the_other_one)
        return self

    async def aclose(self):
        """Clean up resources."""
