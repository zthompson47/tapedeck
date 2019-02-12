"""Reel class."""
from . _transport import Transport


class ReelResident:
    """Something that can be placed in a Reel."""

    def __init__(self):
        """Set up the Reel hooks."""
        self._next_in_reel = None

    @property
    def next_in_reel(self):
        """Return the next in line in this Reel."""
        return self._next_in_reel

    @next_in_reel.setter
    def next_in_reel(self, resident):
        """Set the next in line in this Reel."""
        self._next_in_reel = resident

    def what(self):
        """Do something for pylint."""


class Reel:
    """A stack of spools concatenated in place as one spool in a transport."""

    def __init__(self, spools, announce_to=None, a_announce_to=None):
        """Begin as a list of spools."""
        self._announce = announce_to
        self._a_announce = a_announce_to
        self._spools = spools
        self._message = None
        self._nursery = None

        # Chain the spools together with references.
        for idx, spool in enumerate(self._spools[:-1]):
            spool.next_in_reel = self._spools[idx + 1]

    def __or__(self, the_other_one):
        """Board the __or__ train, creating `Transport` as first in chain."""
        return Transport(self, the_other_one)

    async def aclose(self):
        """Close the spools."""
        for spool in self._spools:
            await spool.aclose()

    @property
    def spools(self):
        """Return the list of spools."""
        return self._spools

    def start_process(self, nursery, message=None):
        """Don't do anything - the spool starts in send..."""
        self._message = message
        self._nursery = nursery

    async def send(self, channel):
        """Send the spools' stdout to the send `channel`."""
        async with channel:

            # Start the first spool.
            if self._spools:
                self._spools[0].start_process(
                    self._nursery, self._message
                )

            for spool in self._spools:

                # Start the next process.
                if spool.next_in_reel:
                    spool.next_in_reel.start_process(
                        self._nursery, self._message
                    )

                # Run the announce callback.
                if self._announce:
                    self._announce(spool)
                elif self._a_announce:
                    await self._a_announce(spool)

                # Send the data and close the proc.
                async with spool.proc:
                    await spool.send_no_close(channel)
