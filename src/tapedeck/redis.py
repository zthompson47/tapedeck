import json
import functools

import trio
from redis import Redis

from .config import REDIS


class RedisProxy:
    def __init__(self, nursery):
        self.request, self.trio_request = trio.open_memory_channel(0)
        self.nursery = nursery
        self.nursery.start_soon(functools.partial(
            trio.to_thread.run_sync, self.redis_thread, cancellable=True
        ))

    def redis_thread(self):
        """Run redis requests synchronously in a thread."""
        redis = Redis(**REDIS)
        while True:
            req = trio.from_thread.run(self.trio_request.receive)
            if req[1] == "set":
                rsp = redis.set(req[2], json.dumps(req[3]))
            elif req[1] == "get":
                rsp = redis.get(req[2])
                result = None
                if rsp:
                    result = json.loads(rsp)
            trio.from_thread.run(req[0].send, result)

    async def get(self, key):
        ch_snd, ch_rcv = trio.open_memory_channel(0)
        await self.request.send((ch_snd, "get", key,))
        return await ch_rcv.receive()

    async def set(self, key, value):
        ch_snd, ch_rcv = trio.open_memory_channel(0)
        await self.request.send((ch_snd, "set", key, value))
        return await ch_rcv.receive()
