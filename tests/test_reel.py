"""Tests for the reel.Reel class."""
import reel


async def test_kill_old_processes(audio_dest):
    """Terminate each process when it finishes streaming."""

    async def checkpoint(spool):
        """Make sure we don't accumulate ffmpeg processes."""
        assert spool
        async with reel.Spool('ps ax') | reel.Spool('grep ffmpeg') as proclist:
            proc_count = len(await proclist.readlines())
            if checkpoint.count == 0:
                checkpoint.count = proc_count
            assert proc_count <= checkpoint.count + 1
    checkpoint.count = 0

    playlist = reel.Reel([reel.cmd.ffmpeg.read(_) for _ in [
        '/Users/zach/out000.wav', '/Users/zach/out001.wav',
        '/Users/zach/out002.wav', '/Users/zach/out003.wav',
        '/Users/zach/out004.wav', '/Users/zach/out005.wav',
        ]], a_announce_to=checkpoint)

    async with playlist | audio_dest() as player:
        await player.play()
        assert player
