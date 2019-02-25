"""Tests for the 'tapedeck play' cli command."""
import logging
import shlex

from reel import Spool

LOG = logging.getLogger(__name__)
LOG.debug('Begin logging for test_cli_play ((o))!!!!!!!!')


async def test_play(env_audio_dest):
    """Stream from source to destination."""
    audio_uri = '/Users/zach/out000.wav'
    player = Spool(
        f'python -m tapedeck.cli.main play {audio_uri} -o {env_audio_dest}'
    )
    await player.timeout(4.7).run()
    assert player.returncode <= 0


async def test_tdplay(audio_uris, env_audio_dest):
    """Stream some audio to nowhere with ``tdplay``."""
    audio_clip = Spool(f"tdplay {audio_uris['wav0']} -o {env_audio_dest}")
    await audio_clip.run()
    assert audio_clip.returncode <= 0


async def test_play_directory(env_audio_dest):
    """Detect a directory and play each song."""
    directory = shlex.quote(
        '/Users/zach/outwav'
    )  # ... test more with quoting and bad characters in filenames ...
    player = Spool(
        f'python -m tapedeck.cli.main play {directory} -o {env_audio_dest}'
    )
    await player.timeout(20).run()
    LOG.debug("error: %s", player.stderr)

    # Either finishes cleanly or times out.
    assert player.returncode == 0 or player.returncode == -9

    # ... need to test sort ...
    # weird how pytest will x-pass even with undefined vars etc


async def test_play_directory_recursive(env_audio_dest):
    """Play a music directory and all subdirectories."""
    directory = shlex.quote(
        '/Users/zach/outwav'
    )
    player = Spool(f'tdplay {directory} -o {env_audio_dest} -r')
    await player.run()
    assert player.returncode == 0


async def test_play_shuffle(env_audio_dest):
    """Shuffle a playlist."""
    directory = shlex.quote(
        '/Users/zach/outwav'
    )
    player = Spool(f'tdplay {directory} -o {env_audio_dest} -s')
    await player.run()
    assert player.returncode == 0
    # need to test actual shuffling, here for coverage...


async def test_play_from_memory(music_dir):
    """Shuffle a playlist."""
    cmd = Spool(f'tdsearch {str(music_dir)}')
    async with cmd as search:
        results = await search.readlines()
        assert len(results) == 3

    cmd2 = Spool('tdplay -m 2')  # speaker coverage here??  oops..
    await cmd2.run()
    assert cmd2.returncode == 0
    # need to test actual playing from memory, here for coverage...


async def test_play_loop():
    """Repeat a playlist forever."""


async def test_udp():
    """Stream music through udp."""
    audio_uri = '/Users/zach/out000.wav'
    player = Spool(
        f'tapedeck play {audio_uri} -o udp --host 127.0.0.1 --port 6969'
    )
    await player.run()
    assert player.returncode == 0


async def test_icecast():
    """Stream music through icecast."""
    audio_uri = '/Users/zach/out000.wav'
    player = Spool(
        f'tapedeck play {audio_uri} -o icecast'
    )
    await player.run()
    assert player.returncode == 0


async def test_output_file(tmpdir):
    """Stream music to an output file."""
    audio_uri = '/Users/zach/out000.wav'
    player = Spool(
        f"tapedeck play {audio_uri} -o {tmpdir.join('out.wav')}"
    )
    await player.run()
    assert player.returncode == 0


async def test_host_port_env_config():
    """Use default host and port from environment variables."""
    audio_uri = '/Users/zach/out000.wav'

    # Try with no host or port.
    player = Spool(f'tapedeck play {audio_uri} -o udp')
    await player.run()
    assert player.returncode > 0
    # assert 'udp needs host and port' in player.err  # ... CAN'T GET STDERR

    # Set a host and port.
    x_env = {'TAPEDECK_UDP_HOST': '127.0.0.1', 'TAPEDECK_UDP_PORT': '9876'}
    player = Spool(f'tapedeck play {audio_uri} -o udp', x_env)
    # await player.run()
    # assert player.status <= 0
