"""Reel class."""
import logging

import trio

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


class Reel(trio.abc.AsyncResource, Streamer):
    """A stack of spools concatenated in place as one spool in a transport."""

    def __init__(self, tracks, announce_to=None, a_announce_to=None):
        """Begin as a list of tracks."""
        logging.debug('|-|-|-|-|-|-|-|-|-|-|->>> NEW REEL')
        self._a_announce = a_announce_to
        self._announce = announce_to
        self._current_track = None
        self._next_track = None
        self._nursery = None
        self._stdin = None
        self._tracks = tracks

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
        # return self._next_track
        if self._next_track:
            logging.debug(
                '==>> %d <<==>> %d <<==',
                self._next_track,
                len(self._tracks)
            )
            return self.tracks[self._next_track]
        return None

    @property
    def current_track(self):
        """Return the currently playing track."""
        # return self._current_track
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
        logging.debug('|-|-|-|-|-|-|-|-|-|-|->>> START REEL')
        self._stdin = stdin
        self._nursery = nursery

        self._queue_next_track()

    def _queue_next_track(self):
        """Set the current/next track so send has something to send."""
        logging.debug('|-|-|-|-|-|-|-|-|-|-|->>> QUEUE_NEXT_TRACK')
        if not self.current_track:
            logging.debug('|-|-|-|-|-|-|-|-|-|-|->>> QUEUE_NEXT_TRACK START')
            self._current_track = 0
            if len(self._tracks) > 1:
                self._next_track = 1
            self.current_track.start(self._nursery, self._stdin)
        else:
            logging.debug('|-|-|-|-|-|-|-|-|-|-|->>> QUEUE_NEXT_TRACK CONT')
            if self._next_track:
                _next = self._next_track + 1
            else:
                _next = None
            self._current_track = self._next_track
            if _next and _next < len(self._tracks):
                self._next_track = _next
            else:
                self._next_track = None

        # Prefetch next track.
        if self.next_track:
            self.next_track.start(self._nursery, self._stdin)

    async def receive(self, channel):
        """Receive input and send it to the current spool."""

    async def send(self, channel):
        """Start each spool and send stdout to the `channel`."""
        logging.debug('|-|-|-|-|-|-|-|-|-|-|->>> SEND')
        async with channel:
            logging.debug('|-|-|-|-|-|-|-|-|-|-|->>> W/CHANNEL')
            while self.current_track:
                logging.debug('|-|->>> SEND %s', self.current_track)

                # Announce the track via callback.
                if self._announce:
                    self._announce(self.current_track)  # _announce_track()?
                elif self._a_announce:
                    await self._a_announce(self.current_track)

                # Play the track.
                logging.debug('|-|->>> SEND about to take proc')
                async with self.current_track.proc:
                    await self.current_track.send_no_close(channel)
                logging.debug('|-|->>> SEND closed proc')

                # Set up the nex track.
                logging.debug('|-|->>> SEND enxt track')
                self._queue_next_track()
