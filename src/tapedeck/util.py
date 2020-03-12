import asyncio
from functools import partial

import trio
from sniffio import current_async_library


class TrioQueue:
    """Wraps a curio.UniversalQueue for trio."""

    def __init__(self, universal_queue):
        self.queue = universal_queue

    async def get(self):
        await trio.hazmat.wait_readable(self.queue)
        request = self.queue._get()
        return request[0]

    async def put(self, item):
        # Should _put be awaitable here?
        self.queue._put(item)


class TrioToAsyncioChannel:
    def __init__(self):
        self.trio_token = trio.hazmat.current_trio_token()
        self.to_asyncio, self.from_trio = trio.open_memory_channel(0)
        self.to_trio, self.from_asyncio = trio.open_memory_channel(0)

    async def send(self, data):
        if current_async_library() == "trio":
            await self.to_asyncio.send(data)
        elif current_async_library() == "asyncio":
            future = asyncio.get_event_loop().run_in_executor(
                None, partial(
                    trio.from_thread.run,
                    self.to_trio.send, data,
                    trio_token=self.trio_token
                )
            )
            await future

    async def receive(self):
        if current_async_library() == "trio":
            return await self.from_asyncio.receive()
        elif current_async_library() == "asyncio":
            future = asyncio.get_event_loop().run_in_executor(
                None, partial(
                    trio.from_thread.run,
                    self.from_trio.receive,
                    trio_token=self.trio_token
                )
            )
            return await future


class CommandRegistry:
    namespace = {}
    def __init__(self, name):
        self.name = name
        self.namespace[name] = {}

    def cmd(self, command_name):
        def decorator(func):
            self.namespace[self.name][command_name] = func
            return func
        return decorator
