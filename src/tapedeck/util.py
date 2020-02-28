import trio


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
