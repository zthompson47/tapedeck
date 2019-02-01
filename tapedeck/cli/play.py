"""The ``tapedeck`` cli 'play' command."""
import random

import blessings
import trio
import trio_click as click

from reel import get_xdg_cache_dir
from reel.cmd import ffmpeg, sox
from reel.io import StreamIO, NullDestStream

from tapedeck.search import find_tunes, is_audio

T = blessings.Terminal()


# pylint: disable=too-many-branches,too-many-locals,too-many-arguments
@click.command(options_metavar='[options]',  # noqa: C901
               help='''¤_play music_¤

                      Use a local file path or a network URL for <source>.
                      Do not provide <source> if using the --cached option.

                    ''')
@click.argument('source', metavar='<source>', required=False)
@click.option('-o', '--output', default='speakers',
              help='Output destination', show_default=True)
@click.option('-s', '--shuffle', help='Shuffle order of tracks', is_flag=True)
@click.option('-r', '--recursive', help='Play subfolders', is_flag=True)
# @click.option('-m', '--memory',\
# help='Play tracks from last search', type=int)
@click.option('-c', '--cached', help='Play track from cached search', type=int)
@click.option('-h', '--host', help='Network streaming host')
@click.option('-p', '--port', help='Network streaming port', type=int)
async def play(source, output, cached, shuffle, host, port, recursive):
    """Build a playlist and play it."""
    playlist = []

    if cached:
        # Find the track filename by index in the cached search results.
        cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
        async with await cache_file.open('r') as out:
            lines = (await out.read()).split('\n')[0:-1]
        track = lines[int(cached) - 1]
        music_path = trio.Path(track[track.find(' ') + 1:])
    else:
        music_path = trio.Path(source)

    if await trio.Path(music_path).is_dir():
        playlist_folders = [music_path]
        if recursive:
            # Run find_tunes on this dir to get all music folders.
            results = await find_tunes(music_path)
            for folder in results:
                playlist_folders.append(trio.Path(folder.path))

        # in a directory, queue each song file
        for folder in playlist_folders:
            songs = [_ for _ in await folder.iterdir() if await _.is_file()]
            songs.sort()
            for song in songs:
                if is_audio(str(song)):
                    playlist.append(await song.resolve())
    else:
        # Otherwise, just queue the uri.
        playlist.append(source)

    out = None
    if output == 'speakers':
        out = sox.play()
    elif output == 'udp':
        out = ffmpeg.udp(host=host, port=port)
    else:
        # Check for file output.
        out_path = trio.Path(output)
        if output == '/dev/null':
            out = NullDestStream()
        elif await out_path.is_file() or await out_path.is_dir():
            out = ffmpeg.to_file(out_path)

    # Shuffle the playlist.
    if shuffle:
        random.shuffle(playlist)  # ... tests needed ...

    async with out:
        for song in playlist:
            if isinstance(song, str):
                click.echo(f'{T.blue}{song}{T.normal}')
            else:
                album_name = f'{T.blue}{song.parent.name}{T.yellow} / '
                song_name = f'{T.blue}{song.name}{T.normal}'
                click.echo(album_name + song_name)
            async with await ffmpeg.stream(str(song)) as src:
                await StreamIO(src, out).flow()
