"""Spool class."""
from time import time
import logging
import os
import shlex
import subprocess

import trio

from . _reel import ReelResident
from . _transport import Transport

LOG = logging.getLogger(__name__)


class Spool(trio.abc.AsyncResource, ReelResident):
    """A command to run as an async subprocess in a ``Transport``."""

    def __init__(self, command, xenv=None, xflags=None):
        """Start a subprocess with a modified argument list and environment."""
        self._command = shlex.split(command)
        self._env = dict(os.environ)
        self._limit = None
        self._proc = None
        self._status = None
        self._stderr = None
        self._timeout = None
        if xflags:
            for flag in xflags:
                # Accept objects like Path that look like a str
                self._command.append(str(flag))
        if xenv:
            for key, val in xenv.items():
                self._env[key] = val
        super().__init__()
        LOG.debug(' '.join(self._command))

    def __str__(self):
        """Print the command."""
        return ' '.join(self._command)

    def __repr__(self):
        """Represent prettily."""
        return f"Spool('{str(self)}')"

    def __or__(self, the_other_one):
        """Create a `Transport` out of the first two spools in the chain."""
        return Transport(self, the_other_one)

    async def __aenter__(self):
        """Run through a tranport in an async managed context."""
        return Transport(self)

    async def aclose(self):
        """Wait for the process to end and close it."""
        await self.proc.aclose()

    @property
    def proc(self):
        """Return the process."""
        return self._proc

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

    # ~= Transport hooks =~

    async def _handle_stderr(self):
        """Read stderr in a function so that the nursery has a function."""
        while True:
            try:
                chunk = await self._proc.stderr.receive_some(16384)
            except trio.ClosedResourceError as err:
                LOG.debug('_handle_stderr: %s', str(err))
                break
            else:
                if not chunk:
                    break
                if not self._stderr:
                    self._stderr = b''
                self._stderr += chunk

    async def _handle_stdin(self, message):
        """Handle stdin."""
        async with self.proc.stdin as stdin:
            await stdin.send_all(message)

    def handle_stderr(self, nursery):
        """Read stderr, called as a task in a nursery."""
        nursery.start_soon(self._handle_stderr)

    def handle_stdin(self, nursery, message):
        """Feed stdin, called as a task in a nursery."""
        nursery.start_soon(self._handle_stdin, message)

    def start_process(self, nursery, message=None):
        """Initialize the subprocess and run the command."""
        self._proc = trio.Process(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._env
        )
        if message:
            self.handle_stdin(nursery, message)
        self.handle_stderr(nursery)

    async def receive(self, channel):
        """Send the output of the receive `channel` to this spool's stdin."""
        async for chunk in channel:
            await self._proc.stdin.send_all(chunk)
        await self._proc.stdin.aclose()  # ??? unless last in chain

    async def send(self, channel):
        """Stream stdout to `channel` and close both sides."""
        async with channel:
            async with self.proc:
                await self.send_no_close(channel)

    async def send_no_close(self, channel):
        """Stream stdout to `channel` without closing either side."""
        buffsize = 16384
        if self._limit and self._limit < 16384:
            buffsize = self._limit
        bytes_received = 0

        # <=~ Receive data.
        try:
            chunk = await self._proc.stdout.receive_some(buffsize)
        except trio.ClosedResourceError as err:
            LOG.exception(err)
            return

        _start_time = time()
        while chunk:

            # ~=> Send data.
            await channel.send(chunk)

            bytes_received += len(chunk)

            # Check for byte limit.
            if self._limit and bytes_received > self._limit:
                break

            # Check for timeout.
            if self._timeout:
                if (time() - _start_time) >= self._timeout:
                    break

            # Cap buffer at limit.
            buffsize = 16384
            if self._limit and self._limit < 16384:
                buffsize = self._limit

            # <=~ Receive data.
            chunk = await self._proc.stdout.receive_some(buffsize)
