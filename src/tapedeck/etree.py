import functools
import asyncio

import feedparser
import anyio
import curio
import trio

from .config import ETREE_RSS_URI, ETREE_RSS_REDIS_KEY

CMD = {}


def cmd(name):
    """Fill etree.CMD with command list via this decorator."""
    def decorator(func):
        CMD[name] = func
        return func
    return decorator


class EtreeProxyBase:
    def __init__(self, redis):
        self.redis = redis

    @cmd("rss")
    async def rss(self):
        return await self.redis.get(ETREE_RSS_REDIS_KEY)

    @cmd("fetch_rss")
    async def fetch_rss(self):
        rss = await self.redis.get(ETREE_RSS_REDIS_KEY)
        kwargs = {}
        if rss:
            kwargs["etag"] = rss.get("etag")
            kwargs["modified"] = rss.get("modified")
        feed = functools.partial(
            feedparser.parse, ETREE_RSS_URI, **kwargs
        )
        rss = await self.get_rss(feed)
        if rss.status != 304:
            await self.redis.set(ETREE_RSS_REDIS_KEY, rss)


class AnyioEtreeProxy(EtreeProxyBase):
    ...
    ... # ok....
    ...
    async def get_rss(self, feed):
        return await anyio.run_in_thread(feed)
    ...
    ...  # JELLOOOOOOO
    ...

class AsyncioEtreeProxy(EtreeProxyBase):
    async def get_rss(self, feed):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(feed)


class CurioEtreeProxy(EtreeProxyBase):
    async def get_rss(self, feed):
        return await curio.run_in_thread(feed)


class TrioEtreeProxy(EtreeProxyBase):
    async def get_rss(self, feed):
        return await trio.to_thread.run_sync(feed, cancellable=True)
