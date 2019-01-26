"""This is reel.output."""
import logging

import trio

__all__ = ['InputStream', 'OutputStream', 'StreamIO']


class StreamIO:
    """A pipe."""

    def __init__(self, producer, consumer):
        """Identify two streams."""
        self._producer = producer
        self._consumer = consumer
        self._byte_limit = None
        self._is_flowing = False

    def is_flowing(self):
        """Filler for pylint."""
        return self._is_flowing

    async def flow(self, byte_limit=None):
        """Connect the two streams."""
        self._is_flowing = True
        async with trio.open_nursery() as nursery:
            send_ch, receive_ch = trio.open_memory_channel(0)
            async with send_ch, receive_ch:
                nursery.start_soon(
                    self._producer.send,
                    send_ch.clone(),
                    byte_limit
                )
                nursery.start_soon(
                    self._consumer.receive,
                    receive_ch.clone()
                )
        self._is_flowing = False


class InputStream:
    """An input stream."""

    def __init__(self, send_stream):
        """Store the real stream."""
        self._send_stream = send_stream

    async def __aenter__(self):
        """."""
        return self

    async def __aexit__(self, *args, **kwargs):
        """."""
        # await self._send_stream.aclose()

    async def __aclose(self):
        """Close up shop."""
        await self._send_stream.aclose()

    async def send_all(self, chunk):
        """."""
        await self._send_stream.send_all(chunk)

    async def receive(self, receive_channel):
        """Stream output from the memory channel."""
        async for chunk in receive_channel:
            await self._send_stream.send_all(chunk)


class OutputStream:
    """An output stream."""

    def __init__(self, receive_stream):
        """Store the real stream."""
        self._receive_stream = receive_stream

    async def __aenter__(self):
        """."""
        return self

    async def __aexit__(self, *args, **kwargs):
        """."""
        await self._receive_stream.aclose()

    async def receive_some(self, max_bytes):
        """."""
        return await self._receive_stream.receive_some(max_bytes)

    async def send(self, send_channel, byte_limit=None):
        """Stream output to the memory channel."""
        buffmax = 16384
        if byte_limit and byte_limit < buffmax:
            buffmax = byte_limit
        chunk = await self._receive_stream.receive_some(buffmax)
        byte_count = len(chunk)
        logging.debug(byte_count)
        async with send_channel:
            while chunk:
                await send_channel.send(chunk)
                if byte_limit and byte_count >= byte_limit:
                    break
                chunk = await self._receive_stream.receive_some(buffmax)
                byte_count += len(chunk)

    async def read_bytes(self, limit=2048):
        """..."""
        _output = b''
        while True:
            chunk = await self._receive_stream.receive_some(limit)
            if not chunk:
                break
            _output += chunk
            if limit:
                if len(_output) >= limit:
                    break
        return _output


class NullDestStream(InputStream):
    """An input stream that goes nowhere."""

    def __init__(self):
        """Store the real stream."""
        super().__init__(self)
        self._send_stream = None

    async def __aenter__(self):
        """."""
        return self

    async def __aexit__(self, *args, **kwargs):
        """."""

    async def __aclose(self):
        """Close up shop."""

    async def send_all(self, chunk):
        """."""

    async def receive(self, receive_channel):
        """Stream output from the memory channel."""
        async for _ in receive_channel:  # noqa: F841
            pass
