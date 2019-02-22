"""Streamer class."""
import abc
import logging

LOG = logging.getLogger(__name__)


class Streamer(metaclass=abc.ABCMeta):
    """Something that can stream i/o in a transport."""

    @abc.abstractmethod
    def start(self, nursery, stdin=None):
        """Start whatever this thing needs to run.

        Called before send or receive.

        """

    async def stop(self):
        """Stop it."""

    async def send_to_channel(self, channel):
        """Send data to the channel and close both sides."""
        LOG.debug('-Streamer- send_to_channel')
        async with channel:
            while True:
                chunk = await self.receive_some(65536)
                if chunk:
                    await channel.send(chunk)
                else:
                    break

    async def receive_from_channel(self, channel):
        """Receive data from the channel."""
        async with channel:
            async for chunk in channel:
                await self.send_all(chunk)

    @abc.abstractmethod
    async def receive_some(self, max_bytes):
        """Return a chunk of data from this stream's output."""

    @abc.abstractmethod
    async def send_all(self, chunk):
        """Send a chunk of data to this stream's input."""
