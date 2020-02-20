import feedparser
import trio

from .config import RSS_ETREE

class EtreeProxy:
    def __init__(self, nursery, redis):
        self.nursery = nursery
        self.to_redis = redis.ch_to_redis
        # TODO test for fetch_rss_task started!!

    async def fetch_rss_task(self):
        ch_to_me, ch_from_redis = trio.open_memory_channel(0)
        while True:
            await trio.sleep(60 * 60)
            rss = await trio.to_thread.run_sync(
                feedparser.parse,
                RSS_ETREE,
                cancellable=True
            )
            await self.to_redis.send(
                (ch_to_me, "set", "etree.rss", rss)
            )

    async def rss(self):
        ch_to_me, ch_from_redis = trio.open_memory_channel(0)
        await self.to_redis.send((ch_to_me, "get", "etree.rss"))
        return await ch_from_redis.receive()
