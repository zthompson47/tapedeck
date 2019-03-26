"""The background process."""
import logging
import subprocess

import trio

from reel.config import get_config, get_xdg_config_dir
from ._server import Server
from ._spool import Spool

LOG = logging.getLogger(__name__)


class Daemon(Spool):
    """A background process."""

    _config_base = None
    _config = dict()

    async def _prepare(self, config):
        """Prepare the config."""

    def __or__(self, next_one):
        """Create a server with the first two spools."""
        return Server([self, next_one])

    def __gt__(self, nursery):
        """Set the nursery to use in the context manager."""
        return Server(self) > nursery

    def __init__(self, command=None, xenv=None, xflags=None):
        """Init the :class:`~reel.Spool`."""
        if command:
            self._command = command
        super().__init__(self._command, xenv=xenv, xflags=xflags)

    async def aclose(self):
        """Terminate the process."""
        if self._proc:
            self._proc.terminate()

    async def __aenter__(self):
        """Open a server context for this daemon."""
        return Server(self)

    async def launch(self, nursery, task_status=trio.TASK_STATUS_IGNORED):
        """Run the daemon."""
        if self._config_base:
            config = await get_config(
                await get_xdg_config_dir(),
                self._config_base,
                **self._config
            )

            # Give the subclasses a chance to fill in configuration vars
            await self._prepare(config)

        self._proc = trio.Process(
            self._command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._env
        )
        nursery.start_soon(self._handle_stdout)
        nursery.start_soon(self._handle_stderr)
        task_status.started()
