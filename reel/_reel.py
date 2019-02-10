"""Reel class."""
from . _transport import Transport


class Reel:
    """A stack of spools concatenated in place as one spool in a transport."""

    def __init__(self, spools, announce_to=None):
        """Begin as a list of spools."""
        self._announce = announce_to
        self._spools = spools
        self._nursery = None

    def __or__(self, the_other_one):
        """Board the __or__ train, creating `Transport` as first in chain."""
        return Transport(self, the_other_one)

    async def aclose(self):
        """Close the spools."""
        for spool in self._spools:
            await spool.aclose()

    # async def handle_stderr(self, nursery):
    #     """Read stderr, called as a task by a Transport in a nursery."""
    #     for spool in self._spools:
    #         nursery.start_soon(spool.handle_stderr, nursery)

    def start_process(self, nursery):
        """Don't do anything - the spool starts in send..."""
        self._nursery = nursery

    async def send(self, channel):
        """Send the spools' stdout to the send `channel`."""
        async with channel:
            for spool in self._spools:
                spool.start_process(self._nursery)
                if self._announce:
                    self._announce(spool)
                await spool.send_no_close(channel)
                await spool.stdout.aclose()
