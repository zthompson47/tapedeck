"""Tests for the reel.Reel class."""
import logging

import trio

from reel import Reel, Spool
from reel.cmd import ffmpeg

LOG = logging.getLogger(__name__)

# pylint: disable=not-async-context-manager


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
            nursery.start_soon(neil_reel.send_to_channel, send_ch)
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


# pylint: disable=too-many-locals
async def test_reels_can_receive_from_channel(tmpdir, neil_reel):
    """A reel can receive a stream and pipe it to the current track."""
    async with trio.open_nursery() as nursery:
        file0 = tmpdir.join('0.wav')
        file1 = tmpdir.join('1.wav')
        file2 = tmpdir.join('2.wav')
        file3 = tmpdir.join('3.wav')
        file4 = tmpdir.join('4.wav')
        output_reel = Reel([
            ffmpeg.to_file(file0),
            ffmpeg.to_file(file1),
            ffmpeg.to_file(file2),
            ffmpeg.to_file(file3),
            ffmpeg.to_file(file4),
        ])
        output_reel.start(nursery)
        neil_reel.start(nursery)
        send_ch, receive_ch = trio.open_memory_channel(0)
        nursery.start_soon(output_reel.receive_from_channel, receive_ch)
        async with send_ch, output_reel:

            lock = trio.Lock()

            chunk0 = await neil_reel.receive_some(65536)
            LOG.debug(b'c0' + chunk0[:47] + chunk0[-47:])
            await send_ch.send(chunk0)

            async with lock:
                await output_reel.skip_to_next_track(close=False)
            chunk1 = await neil_reel.receive_some(65536)
            LOG.debug(b'c1' + chunk1[:47] + chunk1[-47:])
            await send_ch.send(chunk1)

            async with lock:
                await output_reel.skip_to_next_track(close=False)
            chunk2 = await neil_reel.receive_some(65536)
            LOG.debug(b'c2' + chunk2[:47] + chunk2[-47:])
            await send_ch.send(chunk2)

            async with lock:
                await output_reel.skip_to_next_track(close=False)
            chunk3 = await neil_reel.receive_some(65536)
            LOG.debug(b'c2' + chunk3[:47] + chunk3[-47:])
            await send_ch.send(chunk3)

            async with lock:
                await output_reel.skip_to_next_track(close=False)
            chunk4 = b''
            while True:
                _chunk4 = await neil_reel.receive_some(16384)
                if not _chunk4:
                    break
                chunk4 += _chunk4
                await send_ch.send(_chunk4)
            LOG.debug(b'c2' + chunk4[:47] + chunk4[-47:])

        assert await trio.Path(file0).read_bytes() == chunk0
        assert await trio.Path(file1).read_bytes() == chunk1
        assert await trio.Path(file2).read_bytes() == chunk2
        assert await trio.Path(file3).read_bytes() == chunk3
        assert await trio.Path(file4).read_bytes() == chunk4


async def test_reels_can_receive_via_send_all(tmpdir, neil_reel):
    """Receive a stream incrementally in a reel with send_all."""
    # Note - check for prefetching spools with side effects, ie write files..
    async with trio.open_nursery() as nursery:
        file0 = tmpdir.join('0.wav')
        file1 = tmpdir.join('1.wav')
        file2 = tmpdir.join('2.wav')
        output_reel = Reel([
            ffmpeg.to_file(file0),
            ffmpeg.to_file(file1),
            ffmpeg.to_file(file2),
        ])
        output_reel.start(nursery)
        neil_reel.start(nursery)
        async with output_reel, neil_reel:

            # file0
            chunk0 = await neil_reel.receive_some(16384)
            await output_reel.send_all(chunk0)

            # file1
            await output_reel.skip_to_next_track()
            chunk1 = await neil_reel.receive_some(16384)
            await output_reel.send_all(chunk1)

            # file2 - flush the reel to make sure we have complete audio data
            await output_reel.skip_to_next_track()
            chunk2 = b''
            while True:
                _chunk2 = await neil_reel.receive_some(16384)
                if not _chunk2:
                    break
                chunk2 += _chunk2
                await output_reel.send_all(chunk2)

        assert await trio.Path(file0).read_bytes() == chunk0
        assert await trio.Path(file1).read_bytes() == chunk1
        file2_bytes = await trio.Path(file2).read_bytes()

        # The output file is structured differently than input data,
        # so for now it works to just compare the beginning and ending
        # bytes.  I guess..??
        assert file2_bytes[:47] == chunk2[:47]
        assert file2_bytes[-47:] == chunk2[-47:]


async def test_reel_daemon_playing(neil_reel, audio_dest):
    """Detect when a reel is playing."""
    got_here = False
    got_there = False
    async with neil_reel | audio_dest() as player:
        async with trio.open_nursery() as nursery:
            done_evt = player.start_daemon(nursery)
            got_here = True
            while True:
                if done_evt.is_set():
                    got_there = True
                    break
                await trio.sleep(0)
    assert got_here and got_there
