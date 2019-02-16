"""Tests for the reel.Reel class."""
import trio

from reel import Reel, Spool
from reel.cmd import ffmpeg


async def test_kill_old_processes(audio_dest):
    """Terminate each process when it finishes streaming."""

    async def checkpoint(spool):
        """Make sure we don't accumulate ffmpeg processes."""
        assert spool
        async with Spool('ps ax') | Spool('grep ffmpeg') as proclist:
            proc_count = len(await proclist.readlines())
            if checkpoint.count == 0:
                checkpoint.count = proc_count
            assert proc_count <= checkpoint.count + 1
    checkpoint.count = 0

    playlist = Reel([ffmpeg.read(track) for track in [
        '/Users/zach/out000.wav', '/Users/zach/out001.wav',
        '/Users/zach/out002.wav', '/Users/zach/out003.wav',
        '/Users/zach/out004.wav', '/Users/zach/out005.wav',
    ]], a_announce_to=checkpoint)
    async with playlist | audio_dest() as player:
        await player.play()
        assert player


async def test_reel_has_next_track(neil_reel):
    """A reel has a reference to the next track in the reel."""

    # A reel does not have track info until started.
    assert not neil_reel.current_track
    assert not neil_reel.next_track

    # Calculate the expected sequential playlist.
    expected = {}
    for idx, track in enumerate(neil_reel.tracks):
        if idx + 1 < len(neil_reel.tracks):
            expected[track] = neil_reel.tracks[idx + 1]
        elif idx + 1 == len(neil_reel.tracks):
            expected[track] = None

    # Confirm current/next tracks at each announcement.
    def checkpoint(track):
        assert neil_reel.current_track == track
        assert neil_reel.next_track == expected[track]

    neil_reel.announce_to = checkpoint

    # Start the reel and confirm the default sequential playback.
    async with trio.open_nursery() as nursery:
        neil_reel.start(nursery)
        assert neil_reel.current_track == neil_reel.tracks[0]
        assert neil_reel.next_track == neil_reel.tracks[1]

        # Play the reel.
        send_ch, receive_ch = trio.open_memory_channel(0)
        async with send_ch, receive_ch:
            nursery.start_soon(neil_reel.send, send_ch)
            async for chunk in receive_ch:
                # Trigger the checkpoint callback for assertions.
                if chunk:
                    assert chunk


async def test_prefetch_next_track(audio_dest):
    """Start the next subprocess before it's played to start buffering."""

    async def checkpoint(spool):
        """Make sure we don't accumulate ffmpeg processes."""
        assert spool
        async with Spool('ps ax') | Spool('grep ffmpeg') as proclist:
            found_spool = False
            found_next = False
            for line in await proclist.readlines():
                if str(spool) in line:
                    found_spool = True
                if str(spool.next_track) in line:
                    found_next = True
            assert found_spool
            if spool.next_track:
                assert found_next
    assert checkpoint

    playlist = Reel([ffmpeg.read(_) for _ in [
        '/Users/zach/out000.wav', '/Users/zach/out001.wav',
        '/Users/zach/out002.wav', '/Users/zach/out003.wav',
        '/Users/zach/out004.wav', '/Users/zach/out005.wav',
    ]])
    # ]], a_announce_to=checkpoint)
    async with playlist | audio_dest() as player:
        await player.play()
        assert player


async def test_reel_manages_spool_send(neil_reel):
    """A reel can interrupt a spool and divert the stream to another track."""
    async with neil_reel as playlist:
        async with trio.open_nursery() as nursery:
            assert not playlist.current_track
            playlist.start(nursery)
            assert playlist.current_track.pid
            async with Spool('ps ax') | Spool('grep ffmp') as procs:
                found_it = False
                for line in await procs.readlines():
                    if str(playlist.current_track.pid) in line:
                        found_it = True
                assert found_it

            # Play the reel so we can exit.
            while True:
                chunk = await neil_reel.receive_some(16384)
                if not chunk:
                    break
