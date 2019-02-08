"""Handle subprocesses and pipes."""
# pylint --- : disable=R0801
from abc import ABCMeta, abstractmethod
import logging
import os
import shlex

import trio

__all__ = ['Daemon', 'ProcBase']
LIMIT = 163840
LOGGER = logging.getLogger(__name__)


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
        self._proc = trio.Process(
            command,
            stdin=None,
            stdout=None,
            stderr=None,
            env=self._env
        )
