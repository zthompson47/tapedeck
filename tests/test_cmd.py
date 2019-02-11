"""Test the pre-configured commands."""
# import trio

import reel

BYTE_LIMIT = 1000000


async def test_audio_dir(audio_dir):
    """Get test audio files."""
    assert audio_dir.exists()


async def test_import():
    """Make sure the module is imported."""
    assert reel.cmd
    assert reel.cmd.SRC_SILENCE


# async def test_icecast():
#     """Run an icecast server."""
#     cmd = reel.cmd.icecast.Icecast('127.0.0.1', '8676', 'mnt', 'pw')
#     async with cmd as icecast:
#         await icecast.start_daemon()
#         await trio.sleep(1)
#         await icecast.stop()
#
#     async with trio.open_nursery() as nursery:
#         daemon = await reel.Transport(ice).start_daemon(nursery)
#         assert daemon
#         trio.sleep(1)
#         await daemon.stop()
#         assert daemon.returncode == 0


# async def test_icecast():
#     """Run an icecast server."""
#     ice = reel.cmd.icecast.Icecast('127.0.0.1', '8676', 'mnt', 'pw')
#     async with trio.open_nursery() as nursery:
#         daemon = await reel.Transport(ice).start_daemon(nursery)
#         assert daemon
#         trio.sleep(1)
#         await daemon.stop()
#         assert daemon.returncode == 0
