import json
import functools
import trio
from redis import Redis

class RedisProxy:
    def __init__(self, nursery):
        self.nursery = nursery
        self.ch_to_redis, self.ch_from_trio = trio.open_memory_channel(0)
        self.ch_to_trio, self.ch_from_redis = trio.open_memory_channel(0)
        self.nursery.start_soon(self.task_listener)
        self.nursery.start_soon(functools.partial(
            trio.to_thread.run_sync, self.task_proxy, cancellable=True
        ))

    async def task_listener(self):
        while True:
            response = await self.ch_from_redis.receive()
            print(response)

    def task_proxy(self):
        redis = Redis(host="localhost", port=6379, db=0)
        while True:
            req = trio.from_thread.run(self.ch_from_trio.receive)
            if req[1] == "set":
                rsp = redis.set(req[2], json.dumps(req[3]))
            elif req[1] == "get":
                rsp = json.loads(redis.get(req[2]))
            trio.from_thread.run(req[0].send, rsp)
