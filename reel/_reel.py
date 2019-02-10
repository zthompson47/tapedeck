"""Reel class."""
from . _transport import Transport


class Reel:
    """A stack of spools concatenated in place as one spool in a transport."""

    def __init__(self, spools, announce_to=None, a_announce_to=None):
        """Begin as a list of spools."""
        self._announce = announce_to
        self._a_announce = a_announce_to
        self._spools = spools
        self._nursery = None

    def __or__(self, the_other_one):
        """Board the __or__ train, creating `Transport` as first in chain."""
        return Transport(self, the_other_one)

    async def aclose(self):
        """Close the spools."""
        for spool in self._spools:
            await spool.aclose()

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
                elif self._a_announce:
                    await self._a_announce(spool)
                await spool.send_no_close(channel)
                await spool.proc.stdout.aclose()
                await spool.proc.stderr.aclose()
                await spool.proc.stdin.aclose()
                await spool.proc.aclose()
