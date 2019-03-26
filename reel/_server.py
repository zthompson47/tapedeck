"""The background process supervisor."""
import logging

import trio

LOG = logging.getLogger(__name__)


class Server(trio.abc.AsyncResource):
    """A device for running daemon services."""

    def __init__(self, daemon):
        """Get list of daemons ready."""
        self._nursery = None
        if isinstance(daemon, list):
            self._daemons = daemon
        else:
            self._daemons = [daemon]

    def __gt__(self, nursery):
        """Set the nursery to use in the context manager."""
        self._nursery = nursery
        return self

    def __or__(self, next_one):
        """Supervise multiple daemon processes with bitwise or."""
        self._daemons.append(next_one)
        return self

    async def aclose(self):
        """Clean up."""
        for daemon in self._daemons:
            await daemon.aclose()

    async def __aenter__(self):
        """Start up."""
        for daemon in self._daemons:
            await self._nursery.start(daemon.launch, self._nursery)
        return self
