"""Test for the Track class."""
import logging

import trio

from reel import (
    Spool, Streamer, Track, Transport
)

LOG = logging.getLogger(__name__)


async def test_init_echo():
    """Create a Track object that echoes the input to output."""
    echo = Track(lambda _: _)
    assert isinstance(echo, Track)


async def test_start():
    """Start a Track with start() from the Streamer interface."""
    echo = Track(lambda _: _)
    assert isinstance(echo, Streamer)
    async with echo:
        async with trio.open_nursery() as nursery:
            echo.start(nursery)
            nursery.start_soon(echo.send_all, b'asdf')
            assert await echo.receive_some() == b'asdf'
            assert await echo.receive_some() is None


async def test_in_transport():
    """Run a Track in a Transport."""
    async with Track(lambda _: _) as echo:
        assert isinstance(echo, Transport)
        assert await echo.read('asdf') == 'asdf'


async def test_stream_through_track():
    """Stream some data through a Track."""
    async with Spool('cat') | Track(lambda _: _.upper()) as echo_up:
        assert await echo_up.read('this') == 'THIS'
