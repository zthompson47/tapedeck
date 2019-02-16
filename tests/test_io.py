"""Test the pipes."""
# pylint: disable=W0611, W0613, W0621
import logging

import reel


async def test_pipe_operator():
    """Overload the ``__or__`` operator to make piping streams look cool."""
    logging.debug('+++++++++++++++++++++>> BEGIN TEST_PIPE_OPERATOR')

    # Spool some commands
    read_file = reel.Spool(f'cat {__file__}')
    remove_grep = reel.Spool(f'grep -v grep')
    find_cat = reel.Spool('grep cat')

    # One way to make a transport
    transport = reel.Transport(read_file, remove_grep, find_cat)

    # Another way
    chain = [read_file, remove_grep, find_cat]
    transport_chain = reel.Transport(chain)

    # Or:
    async with read_file | remove_grep | find_cat as out:
        assert repr(transport) == repr(transport_chain) == repr(out)
        lines = await out.readlines()
        assert len(lines) == 2
        for line in lines:
            assert 'cat' in line


async def test_play_music_even_better(audio_dest):  # noqa: F811
    """Try pipe operators.
    logging.debug('+++++++++++++++++++++>> BEGIN TEST_PLAY_MUSIC_EVEN_BETTER')

    This method is not gapless.  Reconnecting to the speaker
    on each iteration can (will?) definitely produce some noise.
    Looks cool, though.

    """
    logging.debug('////////////// gaps //////////////////')
    for part in [f'/Users/zach/out00{_}.wav' for _ in range(0, 6)]:
        src = reel.cmd.ffmpeg.read(part).limit(1024**2)
        async with src | audio_dest() as player:
            assert isinstance(player, reel.Transport)
            await player.play()


async def test_play_neil_with_pipes(audio_dest, audio_uri):  # noqa: F811
    """Try pipe operators on the *Come on Baby Let's Go Downtown* intro.

    This method is gapless.  The `Transport` can keep the speaker
    open while switching files.

    """
    logging.debug('+++++++++++++++++++++>> BEGIN TEST_PLAY_NEIL_WITH_PIPES')
    logging.debug('////////////// nogaps ////////////////')
    playlist = reel.Reel([reel.cmd.ffmpeg.read(_).limit(1024**2) for _ in [
        '/Users/zach/out000.wav', '/Users/zach/out001.wav',
        '/Users/zach/out002.wav', '/Users/zach/out003.wav',
        '/Users/zach/out004.wav', '/Users/zach/out005.wav',
        # audio_uri['SONG'], audio_uri['RADIO'],
    ]])
    async with playlist | audio_dest() as player:
        await player.play()
