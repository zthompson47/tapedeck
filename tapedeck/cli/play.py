"""The ``tapedeck`` cli 'play' command."""
import logging
import random
import sys

import blessings
import trio
import trio_click as click

import reel
from reel.config import get_xdg_cache_dir
from reel.cmd import ffmpeg, sox

import tapedeck
from tapedeck.search import find_tunes, is_audio

LOG_LEVEL = trio.run(tapedeck.config.env, 'TAPEDECK_LOG_LEVEL')
if LOG_LEVEL:
    LOG_FILE = trio.run(tapedeck.config.logfile, 'tapedeck.log')
    logging.basicConfig(level=LOG_LEVEL, filename=LOG_FILE)
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler(sys.stderr))
LOGGER.debug('--------->> PLAY!!')

T = blessings.Terminal()


# pylint: disable=too-many-branches,too-many-locals,too-many-arguments
@click.command(  # noqa: C901
    options_metavar='[options]',
    help=f'{T.blue}¤ {T.yellow}Play Music{T.normal}'
)
@click.argument('source', metavar='<source>', required=False)
@click.option('-o', '--output', default='speakers',
              help='Output destination', show_default=True)
@click.option('-s', '--shuffle', help='Shuffle order of tracks', is_flag=True)
@click.option('-r', '--recursive', help='Play subfolders', is_flag=True)
# @click.option('-m', '--memory',\
# help='Play tracks from last search', type=int)
@click.option('-m', '--memory', help='Play track from memory', type=int)
@click.option('-h', '--host', envvar='TAPEDECK_UDP_HOST',
              help='Network streaming host')
@click.option('-p', '--port', envvar='TAPEDECK_UDP_PORT',
              help='Network streaming port', type=int)
async def play(source, output, memory, shuffle, host, port, recursive):
    """Build a playlist and play it."""
    playlist = []

    if memory:
        # Find the track filename by index in the cached search results.
        cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
        async with await cache_file.open('r') as out:
            lines = (await out.read()).split('\n')[0:-1]
        track = lines[int(memory) - 1]
        music_path = reel.Path(track[track.find(' ') + 1:])
    else:
        music_path = reel.Path(source)

    if await reel.Path(music_path).is_dir():
        playlist_folders = [music_path]
        if recursive:
            # Run find_tunes on this dir to get all music folders.
            results = await find_tunes(music_path)
            for folder in results:
                playlist_folders.append(reel.Path(folder.path))

        # in a directory, queue each song file
        for folder in playlist_folders:
            songs = [_ for _ in await folder.iterdir() if _.is_file()]
            songs.sort()
            for song in songs:
                if is_audio(str(song)):
                    playlist.append(song)
    else:
        # Otherwise, just queue the uri.
        playlist.append(source)

    # Shuffle the playlist.
    if shuffle:
        random.shuffle(playlist)  # ... tests needed ...

    # Choose the output.
    out = None
    if output == 'speakers':
        out = sox.speakers()
    elif output == 'udp':
        if host is None or port is None:
            raise click.BadOptionUsage('-o', 'udp needs host and port')
        out = ffmpeg.to_udp(host=host, port=port)
    else:
        # Check for file output.
        out_path = reel.Path(output)
        if (output == '/dev/null' or
                await out_path.is_file() or
                await out_path.is_dir()):
            out = ffmpeg.to_file2(out_path)

    # Create the playlist.
    plst = reel.Reel(
        [ffmpeg.read(track) for track in playlist],
        announce_to=click.echo
    )

    # Fire away!!
    async with plst | out as transport:
        await transport.play()

OLD = '''
#     out = None
#     if output == 'speakers':
#         out = sox.play()
#     elif output == 'udp':
#         if host is None or port is None:
#             raise click.BadOptionUsage('-o', 'udp needs host and port')
#         out = ffmpeg.udp(host=host, port=port)
#     else:
#         # Check for file output.
#         out_path = reel.Path(output)
#         if output == '/dev/null':
#             out = NullDestStream()
#         elif await out_path.is_file() or await out_path.is_dir():
#             out = ffmpeg.to_file(out_path)
#
#     async with out:
#         for song in playlist:
#             if isinstance(song, str):
#                 click.echo(f'{T.blue}{song}{T.normal}')
#             else:
#                 album_name = f'{T.blue}{song.parent.name}{T.yellow} / '
#                 song_name = f'{T.blue}{song.name}{T.normal}'
#                 click.echo(album_name + song_name)
#             async with await ffmpeg.stream(str(song)) as src:
#                 await StreamIO(src, out).flow()
'''
