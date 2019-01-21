"""This is reel.output."""
import trio

__all__ = ['Input', 'Output', 'Through']


class Through:
    """."""

    def __init__(self):
        """."""

    def yup(self):
        """."""

    def bup(self):
        """."""


class Input(trio.abc.SendStream):
    """."""

    def __init__(self, send_stream):
        """Store the real stream."""
        self._send_stream = send_stream

    async def __aenter__(self):
        """Enter the stream context."""
        await self._send_stream.__aenter__()
        return self

    async def __aexit__(self, *args):
        """Exit the stream context."""
        await self._send_stream.__aexit__(*args)

    async def aclose(self):
        """Implement trio.AsyncResource and behave nicely."""
        await self._send_stream.aclose()

    async def send_all(self, data):
        """Impl."""
        await self._send_stream.send_all(data)

    async def wait_send_all_might_not_block(self):
        """Impl."""
        await self._send_stream.wait_send_all_might_not_block()


class Output(trio.abc.ReceiveStream):
    """An output stream."""

    def __init__(self, receive_stream):
        """Store the real stream."""
        self._receive_stream = receive_stream

    async def __aenter__(self):
        """Enter the stream context."""
        await self._receive_stream.__aenter__()
        return self

    async def __aexit__(self, *args):
        """Exit the stream context."""
        await self._receive_stream.__aexit__(*args)

    async def aclose(self):
        """Implement trio.AsyncResource and behave nicely."""
        await self._receive_stream.aclose()

    async def receive_some(self, max_bytes):
        """..."""
        return await self._receive_stream.receive_some(max_bytes)

    async def read_bytes(self, limit=2048):
        """..."""
        _output = b''
        # async with self._receive_stream as out:
        print('before True---------------------------')
        while True:
            print('after True---------------------------')
            chunk = await self._receive_stream.receive_some(limit)
            print(f'after chundk-------f{len(chunk)}--------------------')
            if not chunk:
                break
            _output += chunk
            if limit:
                if len(_output) >= limit:
                    break
        return _output
