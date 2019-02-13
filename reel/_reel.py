"""Reel class."""
from ._transport import Streamer, Transport


class Track:
    """Something that can be placed in a Reel."""

    def __init__(self):
        """Set up the Reel hooks."""
        self._next_track = None

    @property
    def next_track(self):
        """Return the next in line in this Reel."""
        return self._next_track

    @next_track.setter
    def next_track(self, track):
        """Set the next in line in this Reel."""
        self._next_track = track

    def what(self):
        """Do something for pylint."""


class Reel(Streamer):
    """A stack of spools concatenated in place as one spool in a transport."""

    def __init__(self, tracks, announce_to=None, a_announce_to=None):
        """Begin as a list of tracks."""
        self._a_announce = a_announce_to
        self._announce = announce_to
        self._now_playing = None
        self._nursery = None
        self._stdin = None
        self._tracks = tracks

        # Create a list of spools.
        for idx, track in enumerate(self._tracks[:-1]):
            track.next_track = self._tracks[idx + 1]

    def __or__(self, the_other_one):
        """Board the __or__ train, creating `Transport` as first in chain."""
        return Transport(self, the_other_one)

    async def aclose(self):
        """Close the spools."""
        for track in self._tracks:
            await track.aclose()

    @property
    def spools(self):
        """Return the list of spools."""
        return self._tracks

    def start_process(self, nursery, stdin=None):
        """Store information for send to use."""
        self._stdin = stdin
        self._nursery = nursery

    async def receive(self, channel):
        """Receive input and send it to the current spool."""

    async def send(self, channel):
        """Start each spool and send stdout to the `channel`."""
        async with channel:

            # while ...

            # Start the first spool.
            if self._tracks:
                self._tracks[0].start_process(self._nursery, self._stdin)

            for spool in self._tracks:

                # Start the next process.
                if spool.next_track:
                    spool.next_track.start_process(self._nursery, self._stdin)

                # Run the announce callback.
                if self._announce:
                    self._announce(spool)
                elif self._a_announce:
                    await self._a_announce(spool)

                # Send the data and close the proc.
                async with spool.proc:
                    await spool.send_no_close(channel)
