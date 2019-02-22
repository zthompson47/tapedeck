"""Track class."""
import logging

import trio

from ._streamer import Streamer
from ._transport import Transport

LOG = logging.getLogger(__name__)


class Track(trio.abc.AsyncResource, Streamer):
    """Something that can produce a stream."""

    def __init__(self, func):
        """Store a function for later use."""
        LOG.debug('-- || TRACK __init__ %s', str(func))
        self._func = func
        self._nursery = None
        self._stdout = None
        self._snd_ch, self._rcv_ch = trio.open_memory_channel(0)

    def __or__(self, the_other_one):
        """Create a `Transport` out of the first two spools in the chain."""
        return Transport(self, the_other_one)

    async def __aenter__(self):
        """Run through a tranport in an async managed context."""
        LOG.debug('-- || TRACK __aenter__ %s', str(self._func))
        return Transport(self)

    async def aclose(self):
        """Close down the Track."""

    def start(self, nursery, stdin=None):
        """Begin the process of creating a data stream."""
        self._nursery = nursery
        if stdin:
            nursery.start_soon(self.send_all, stdin)

    async def send_all(self, chunk):
        """Send a chunk of data to the input of this stream."""
        LOG.debug('00000000000000000 send_all %s', chunk)
        async with self._snd_ch:
            LOG.debug('0001 in asun %s %s', chunk, self._func(chunk))
            await self._snd_ch.send(self._func(chunk))
            LOG.debug('0002 in asun %s', chunk)
            await self._snd_ch.send(None)
            LOG.debug('0003 in asun %s', chunk)

    async def receive_some(self, max_bytes=65536):
        """Return a chunk of data from the output of this stream."""
        LOG.debug('-- || >> TRACK receive_some START')
        # async with self._rcv_ch:
        result = await self._rcv_ch.receive()
        LOG.debug('-- || >> TRACK receive_some aft rec')
        if not result:
            await self._rcv_ch.aclose()
        return result
