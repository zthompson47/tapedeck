"""Unit tests for spools."""
import trio

from reel import Spool


async def test_spool_send_chunk():
    """A spool can send its output one chunk at a time."""
    now = Spool("date '+%Y-%m-%d'")
    async with now:
        async with trio.open_nursery() as nursery:
            now.start(nursery)
            assert now.pid
