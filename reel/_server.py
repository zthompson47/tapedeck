"""The background process supervisor."""
import logging

import trio

LOG = logging.getLogger(__name__)


class Server(trio.abc.AsyncResource):
    """A device for running daemon services."""

    def __init__(self, daemon):
        """Get list of daemons ready.

        Examples:
            >>> from reel import Server
            >>> from reel.cmd import Icecast, Redis
            >>> assert Server(Redis())
            >>> assert Server([Redis(), Icecast()])

        """
        if isinstance(daemon, list):
            self._daemons = daemon
        else:
            self._daemons = [daemon]

    def __or__(self, next_one):
        """Supervise multiple daemon processes with bitwise or.

        Examples:
            >>> from reel.cmd import Icecast, Redis
            >>> server = Icecast() | Redis()
            >>> assert isinstance(server, Server)

        """
        self._daemons.append(next_one)
        return self

    async def aclose(self):
        """Clean up."""
        # print('claenine up')
        for daemon in self._daemons:
            # print(f'daemon shuting down: {daemon}')
            await daemon.aclose()
            # print(f'daemon shut DOWN: {daemon}')

    async def run(self, nursery, task_status=trio.TASK_STATUS_IGNORED):
        """Start up."""
        LOG.debug(self._daemons)
        for daemon in self._daemons:
            await nursery.start(daemon.launch, nursery)
        task_status.started()
