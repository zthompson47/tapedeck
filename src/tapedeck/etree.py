"""Etree <http://bt.etree.org> RSS feed."""
from functools import partial

import feedparser
import trio

from .config import ETREE_RSS_URI, ETREE_RSS_REDIS_KEY
from .util import CommandRegistry


class EtreeProxy:
    """RSS feed."""

    def __init__(self, redis):
        self.redis = redis

    cmd = CommandRegistry("etree").cmd

    @cmd("rss")
    async def rss(self):
        """Show the current feed."""
        return await self.redis.get(ETREE_RSS_REDIS_KEY)

    @cmd("fetch_rss")
    async def fetch_rss(self):
        """Fetch a new feed."""
        rss = await self.redis.get(ETREE_RSS_REDIS_KEY)
        kwargs = {}
        if rss:
            kwargs["etag"] = rss.get("etag")
            kwargs["modified"] = rss.get("modified")
        feed = partial(
            feedparser.parse, ETREE_RSS_URI, **kwargs
        )
        rss = await trio.to_thread.run_sync(feed, cancellable=True)
        if rss.status != 304:
            await self.redis.set(ETREE_RSS_REDIS_KEY, rss)
