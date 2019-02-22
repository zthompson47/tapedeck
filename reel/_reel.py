"""Reel class."""
import logging

import trio

from ._streamer import Streamer
from ._transport import Transport

LOG = logging.getLogger(__name__)


class Reel(trio.abc.AsyncResource, Streamer):
    """A stack of spools concatenated in place as one spool in a transport."""

    def __init__(self, tracks, announce_to=None, a_announce_to=None):
        """Begin as a list of tracks."""
        self._a_announce = a_announce_to
        self._announce = announce_to
        self._current_track = None
        self._next_track = None
        self._nursery = None
        self._stdin = None
        self._tracks = tracks

    def __str__(self):
        """Print the command."""
        return self.__repr__()

    def __repr__(self):
        """Represent prettily."""
        result = 'Reel([ '
        for track in self._tracks:
            result += track.__repr__()
            result += ','
        result += ' ])'
        return result

    def __or__(self, the_other_one):
        """Board the __or__ train, creating `Transport` as first in chain."""
        return Transport(self, the_other_one)

    async def aclose(self):
        """Close the spools."""
        for track in self._tracks:
            await track.aclose()

    @property
    def announce_to(self):
        """Return the next track on deck."""
        return self._announce

    @announce_to.setter
    def announce_to(self, value):
        """Set the announce_to callback."""
        self._announce = value

    @property
    def announce_to_async(self):
        """Return the next track on deck."""
        return self._a_announce

    @announce_to_async.setter
    def announce_to_async(self, value):
        """Set the announce_to callback."""
        self._a_announce = value

    @property
    def next_track(self):
        """Return the next track on deck."""
        if self._next_track:
            return self.tracks[self._next_track]
        return None

    @property
    def current_track(self):
        """Return the currently playing track."""
        if self._current_track is not None:
            return self._tracks[self._current_track]
        return None

    @property
    def tracks(self):
        """Return the list of tracks."""
        return self._tracks

    @property
    def spools(self):
        """Return the list of spools."""
        return self._tracks

    def start(self, nursery, stdin=None):
        """Store information for send to use."""
        LOG.debug('[ START REEL %d ]', len(self._tracks))
        self._nursery = nursery
        self._stdin = stdin
        self._start_next_track()

    async def stop(self):
        """Stop it."""

    def _start_next_track(self):
        """Set the current/next track so send has something to send."""
        LOG.debug(
            '[ REEL %d START NEXT_TRACK %s %s ]',
            len(self._tracks),
            str(self._current_track),
            str(self._next_track)
        )

        # Start at the beginning without a current track.
        if not self.current_track:
            if self._tracks:
                self._current_track = 0
                if len(self._tracks) > 1:
                    self._next_track = 1
            self.current_track.start(self._nursery, self._stdin)
        else:
            _next = None
            if self._next_track:
                _next = self._next_track + 1
            self._current_track = self._next_track
            if _next and _next < len(self._tracks):
                self._next_track = _next
            else:
                self._next_track = None

        # Prefetch next track by starting it.
        if self.next_track:
            self.next_track.start(self._nursery, self._stdin)

        LOG.debug(
            '[ REEL %d STARTED NEXT_TRACK %s %s ]',
            len(self._tracks),
            str(self._current_track),
            str(self._next_track)
        )

    async def skip_to_next_track(self, close=True):
        """Begin playing the next track immediately."""
        LOG.debug(
            '[ REEL %d SKIP_TO_NEXT_TRACK %s %s ]',
            len(self._tracks),
            self._current_track,
            self._next_track
        )
        if close:
            await self.current_track.aclose()

        if self.next_track:
            self._start_next_track()

            # Announce the track change.
            if self._announce:
                self._announce(self.current_track)
            elif self._a_announce:
                await self._a_announce(self.current_track)

    async def receive_from_channel(self, channel):
        """Receive input and send it to the current spool."""
        LOG.debug(
            '[ REEL track[%s] receive_from_channel() ]',
            str(self._current_track)
        )
        async with channel:
            async for chunk in channel:
                LOG.debug(b'ZZ' + chunk[:47] + chunk[-47:])
                await self.send_all(chunk)

    async def send_all(self, chunk):
        """Receive input and send it to the current spool."""
        LOG.debug(
            '[ REEL track[%s] send_all !! len %d ]',
            str(self._current_track),
            len(chunk)
        )
        if self.current_track:  # race??  next line could be error?
            LOG.debug('[ REEL send_all !! len %d ALMOST !!]', len(chunk))
            await self.current_track.send_all(chunk)
        LOG.debug('[ REEL send_all !! len %d DONE !!]', len(chunk))

    async def receive_some(self, max_bytes):
        """Return a chunk of data from the output of this stream."""
        if self.current_track:

            # Return a chunk of data from the current track.
            chunk = await self.current_track.receive_some(max_bytes)
            if chunk:
                return chunk

            # No data, close the track and start the next one.
            await self.current_track.proc.aclose()
            if self.next_track:
                self._start_next_track()

                # Announce the track change.
                if self._announce:
                    self._announce(self.current_track)
                elif self._a_announce:
                    await self._a_announce(self.current_track)

                # Return a chunk of data from the new track.
                return await self.receive_some(max_bytes)

        # Send empty byte as EOF.
        return b''

    async def send_to_channel(self, channel):
        """Start each spool and send stdout to the `channel`."""
        async with channel:
            while self.current_track:

                # Announce the track change.
                if self._announce:
                    self._announce(self.current_track)
                elif self._a_announce:
                    await self._a_announce(self.current_track)

                # Play the track.
                while True:
                    chunk = await self.receive_some(16384)
                    if chunk:
                        await channel.send(chunk)
                    else:
                        break
                self._start_next_track()
