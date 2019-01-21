"""Handle subprocesses and pipes."""
from abc import ABCMeta, abstractmethod
import os
import shlex

import trio

from reel.io import Input, Output

__all__ = ['Daemon', 'Destination', 'Source']
LIMIT = 163840


class ProcBase(metaclass=ABCMeta):
    """Base class for subprocesses."""

    def __init__(self, command, xenv=None, xconf=None):
        """Initialize the server."""
        self._command = shlex.split(command)
        if xconf:
            for flag in xconf:
                self._command.append(shlex.quote(flag))
        self._env = os.environ
        if xenv:
            for key, val in xenv.items():
                self._env[key] = val
        self._proc = None
        self._status = None

    @abstractmethod
    async def prepare_command(self):
        """Prepare a command to start the process."""
        return self._command

    async def __aenter__(self):
        """Enter the server context."""
        return self

    async def __aexit__(self, *args):
        """Exit the server context."""
        if self._proc:
            self._proc.terminate()
            await self._proc.aclose()


class Daemon(ProcBase):
    """A server process."""

    async def prepare_command(self):
        """Return the command for this process."""
        return self._command

    async def start(self):
        """Start the server."""
        command = await self.prepare_command()
        self._proc = trio.subprocess.Process(
            command,
            stdin=None,
            stdout=None,
            stderr=None,
            env=self._env
        )


class Destination:
    """A subprocess that consumes input."""

    _command = None
    _env = os.environ
    _nurse = None
    _status = None

    def __init__(self, command, xenv=None, xconf=None):
        """Get the command ready to run."""
        self._command = shlex.split(command)
        self._proc = None
        if xconf:
            for flag in xconf:
                self._command.append(flag)
        if xenv:
            for key, val in xenv.items():
                self._env[key] = val
        print(' '.join(self._command))

    async def __aenter__(self):
        """Hijack ``trio._core._run.NurseryManager``."""
        self._nurse = trio.open_nursery()
        await self._nurse.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        """Close the nursery."""
        await self._nurse.__aexit__(exc_type, exc, traceback)

    @property
    def status(self):
        """Return the command exit code."""
        return self._status

    async def receive(self):
        """Return a context-managed output stream."""
        self._proc = trio.subprocess.Process(
            self._command,
            stdin=trio.subprocess.PIPE,
            stdout=None,
            stderr=None,
            env=self._env
        )
        return Input(self._proc.stdin)


class Source():
    """A subprocess that produces output."""

    _command = None
    _env = os.environ
    _err = b''
    _limit = LIMIT
    _nurse = None
    _output = b''
    _proc = None
    _status = None
    _stream = False

    def __init__(self, command, xenv=None, xconf=None):
        """Get the command ready to run."""
        self._command = shlex.split(command)
        if xconf:
            for flag in xconf:
                self._command.append(flag)
        if xenv:
            for key, val in xenv.items():
                self._env[key] = val
        print(' '.join(self._command))

    async def __aenter__(self):
        """Hijack ``trio._core._run.NurseryManager``."""
        self._nurse = trio.open_nursery()
        await self._nurse.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        """Close the nursery."""
        await self._nurse.__aexit__(exc_type, exc, traceback)

    @property
    def cmd(self):
        """Return the original command."""
        return ' '.join(self._command)

    @property
    def err(self):
        """Decode stderr."""
        result = []
        decoded = self._err.decode('utf-8').strip()
        for byte in decoded:
            if byte == '':
                result.pop()
            else:
                result.append(byte)
        return ''.join(result)

    @property
    def status(self):
        """Return the command exit code."""
        return self._status

    async def _stream_stderr(self, limit):
        """..."""
        async with self._proc.stderr as err:  # type: trio.abc.ReceiveStream
            while True:
                chunk = await err.receive_some(limit)
                if not chunk:
                    break
                self._err += chunk
                if limit:
                    if len(self._err) >= limit:
                        break

    async def _stream_stdout(self, limit):
        """..."""
        async with self._proc.stdout as out:
            while True:
                if limit:
                    chunk_size = limit
                else:
                    chunk_size = 16384
                chunk = await out.receive_some(chunk_size)
                if not chunk:
                    break
                self._output += chunk
                if limit:
                    if len(self._output) >= limit:
                        break

    async def _stream_stdin(self, message):
        """..."""
        async with self._proc.stdin as stdin:
            try:
                await stdin.send_all(message)
            except trio.BrokenResourceError:
                pass

    async def run(self, message=None):
        """Run the command."""
        if message:
            message = message.encode('utf-8')
            _stdin = trio.subprocess.PIPE
        else:
            _stdin = None
        self._proc = trio.subprocess.Process(
            self._command,
            stdin=_stdin,
            stdout=None,
            stderr=None,
            env=self._env
        )
        if message:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(self._stream_stdin, message)
        await self._proc.wait()
        self._status = self._proc.returncode
        return self._output.decode('utf-8').strip()

    async def read_bool(self, stdin=None):
        """Run the command and return the exit status."""
        if stdin:
            stdin = stdin.encode('utf-8')
            _stdin = trio.subprocess.PIPE
        else:
            _stdin = None
        self._proc = trio.subprocess.Process(
            self._command,
            stdin=_stdin,
            stdout=trio.subprocess.PIPE,
            stderr=trio.subprocess.PIPE,
            env=self._env
        )
        async with trio.open_nursery() as nursery:
            if _stdin == trio.subprocess.PIPE:
                nursery.start_soon(self._stream_stdin, stdin)
            nursery.start_soon(self._stream_stderr, self._limit)
            nursery.start_soon(self._stream_stdout, self._limit)
            await self._proc.wait()
            self._status = self._proc.returncode
        return self.status == 0

    async def read_text(self, message=None):
        """Run the command and return the output."""
        if message:
            message = message.encode('utf-8')
            _stdin = trio.subprocess.PIPE
        else:
            _stdin = None
        self._proc = trio.subprocess.Process(
            self._command,
            stdin=_stdin,
            stdout=trio.subprocess.PIPE,
            stderr=trio.subprocess.PIPE,
            env=self._env
        )
        async with trio.open_nursery() as nursery:
            if _stdin == trio.subprocess.PIPE:
                nursery.start_soon(self._stream_stdin, message)
            nursery.start_soon(self._stream_stderr, self._limit)
            nursery.start_soon(self._stream_stdout, self._limit)
            await self._proc.wait()
            self._status = self._proc.returncode
        return self._output.decode('utf-8').strip()

    async def read_bytes(self, send_bytes=None):
        """Run the command and return the output."""
        if send_bytes:
            _stdin = trio.subprocess.PIPE
        else:
            _stdin = None
        self._proc = trio.subprocess.Process(
            self._command,
            stdin=_stdin,
            stdout=trio.subprocess.PIPE,
            stderr=trio.subprocess.PIPE,
            env=self._env
        )
        async with trio.open_nursery() as nursery:
            if _stdin == trio.subprocess.PIPE:
                nursery.start_soon(self._stream_stdin, send_bytes)
            nursery.start_soon(self._stream_stderr, self._limit)
            nursery.start_soon(self._stream_stdout, None)
            await self._proc.wait()
            self._status = self._proc.returncode
        return self._output

    async def read_list(self, message=None, through=None):
        """Return the output as a list."""
        output = await self.read_text(message)
        output_list = output.split('\n')
        if through:
            return [await through(_) for _ in output_list]
        return output_list

    async def stream(self, message=None):
        """Return a context-managed output stream."""
        if message:
            message = message.encode('utf-8')
            _stdin = trio.subprocess.PIPE
        else:
            _stdin = None
        self._proc = trio.subprocess.Process(
            self._command,
            stdin=_stdin,
            stdout=trio.subprocess.PIPE,
            stderr=None,
            env=self._env
        )
        if message:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(self._stream_stdin, message)
        return Output(self._proc.stdout)
