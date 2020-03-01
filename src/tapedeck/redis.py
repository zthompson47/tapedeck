import json
from functools import partial
import asyncio
import threading

import anyio
import curio
import trio
from redis import Redis

from .config import REDIS


class AsyncioRedisProxy:
    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.request = asyncio.Queue()
        self.response = asyncio.Queue()
        self.thread = threading.Thread(target=self.redis_thread)
        self.thread.start()

    def redis_thread(self):
        """Run redis requests synchronously in a thread."""
        redis = Redis(**REDIS)
        while True:
            req = asyncio.run_coroutine_threadsafe(
                self.request.get(), self.loop
            ).result()
            if req[1] == "set":
                rsp = redis.set(req[2], json.dumps(req[3]))
            elif req[1] == "get":
                rsp = redis.get(req[2])
                result = None
                if rsp:
                    result = json.loads(rsp)
            asyncio.run_coroutine_threadsafe(req[0].put(result), self.loop)

    async def get(self, key):
        answer = asyncio.Queue()
        await self.request.put((answer, "get", key,))
        return await answer.get()

    async def set(self, key, value):
        answer = asyncio.Queue()
        await self.request.put((answer, "set", key, value))
        return await answer.get()


class AnyioRedisProxy:
    def __init__(self, task_group):
        self.request = anyio.create_queue(0)
        self.tg = task_group

    async def __aenter__(self):
        await self.tg.spawn(partial(
            anyio.run_in_thread, self.redis_thread, cancellable=True
        ))
        return self

    async def __aexit__(self, *args):
        import logging
        logging.debug("-----------------------!!!!!!!!!!!!!!!!!!!!!!!!!!1")
        pass

    def redis_thread(self):
        """Run redis requests synchronously in a thread."""
        async def arun(func):
            """Use async fn in local context so anyio can
            find the asyncio event loop."""
            return await func()
        redis = Redis(**REDIS)
        while True:
            req = anyio.run_async_from_thread(arun, self.request.get)
            if req[1] == "set":
                rsp = redis.set(req[2], json.dumps(req[3]))
            elif req[1] == "get":
                rsp = redis.get(req[2])
                result = None
                if rsp:
                    result = json.loads(rsp)
            elif req[1] is None:
                break
            anyio.run_async_from_thread(arun, partial(req[0].put, result))

    async def get(self, key):
        answer = anyio.create_queue(0)
        await self.request.put((answer, "get", key,))
        return await answer.get()

    async def set(self, key, value):
        answer = anyio.create_queue(0)
        await self.request.put((answer, "set", key, value))
        return await answer.get()

    async def close(self):
        await self.request.put((None, None,))


class CurioRedisProxy:
    def __init__(self):
        self.request = curio.Queue()
        self.response = curio.Queue()

    async def start(self):
        self.thread = await curio.thread.spawn_thread(self.redis_thread)

    def redis_thread(self):
        """Run redis requests synchronously in a thread."""
        redis = Redis(**REDIS)
        while True:
            req = curio.thread.AWAIT(self.request.get)
            if req[1] == "set":
                rsp = redis.set(req[2], json.dumps(req[3]))
            elif req[1] == "get":
                rsp = redis.get(req[2])
                result = None
                if rsp:
                    result = json.loads(rsp)
            curio.thread.AWAIT(req[0].put, result)

    async def get(self, key):
        answer = curio.Queue()
        await self.request.put((answer, "get", key,))
        return await answer.get()

    async def set(self, key, value):
        answer = curio.Queue()
        await self.request.put((answer, "set", key, value))
        return await answer.get()


class TrioRedisProxy:
    def __init__(self, nursery):
        self.request, self.trio_request = trio.open_memory_channel(0)
        self.nursery = nursery
        self.nursery.start_soon(
            partial(
                trio.to_thread.run_sync, self.redis_thread, cancellable=True
            )
        )

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
