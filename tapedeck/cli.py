"""The command line interface to tapedeck."""
import random

import ansicolortags
import trio
import trio_click as click

from reel.cmd import ffmpeg, sox
from reel.config import get_xdg_cache_dir
from reel.io import StreamIO, NullDestStream
from reel.tools import click_echof

import tapedeck
from tapedeck.search import find_tunes, is_audio

# pylint: disable=no-value-for-parameter


@click.group(
    invoke_without_command=True,
    context_settings=dict(help_option_names=['--help']),
    options_metavar='<options>',
    help='¤- Manage your music'
)
@click.option('-v', '--version', is_flag=True,
              help=f'Print "{tapedeck.__version__}" and exit.')
async def main(version):
    """Enter the tapedeck cli."""
    if version:
        await click_echof(tapedeck.__version__)


@main.command(options_metavar='[options]',
              help='¤- Find your music')
@click.argument('directory', metavar='[directory]', required=False)
@click.option('-d', '--follow-dots', is_flag=True,
              help='Search hidden dot-directories.')
@click.option('-l', '--follow-links', is_flag=True,
              help='Search symlinked directories.')
@click.option('-c', '--cached', is_flag=True,
              help='Show cached search history')
async def search(directory, follow_links, follow_dots, cached):
    """Search for music."""
    if cached:
        cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
        async with await cache_file.open('r') as out:
            lines = (await out.read()).split('\n')[0:-1]
        output = []
        for line in lines:
            number = line[0:line.find(' ')]
            filename = line[line.find(' ') + 1:]
            path = trio.Path(filename)
            output.append(f' <green>{number} <blue>{path.name}<reset>')
        click.echo_via_pager(ansicolortags.sprint('\n'.join(output)))
        return

    results = await find_tunes(
        directory,
        followlinks=follow_links,
        followdots=follow_dots
    )
    idx = 0
    for folder in results:
        idx += 1
        path = trio.Path(folder.path)
        await click_echof(f'  <green>{idx}. <blue>{path.name}<reset>')

    # Store results in a cache file.
    cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
    async with await cache_file.open('w') as out:
        idx = 0
        for folder in results:
            idx += 1
            await out.write(f'{idx}. {str(folder.path)}\n')


# pylint: disable=too-many-branches,too-many-locals,too-many-arguments
@main.command(options_metavar='[options]',  # noqa: C901
              help='¤- Play your music')
@click.argument('source', metavar='[source]', required=False)
@click.option('-o', '--output', default='speakers',
              help='Output destination', show_default=True)
@click.option('-s', '--shuffle', help='Shuffle order of tracks', is_flag=True)
@click.option('-r', '--recursive', help='Play subfolders', is_flag=True)
@click.option('-c', '--cached', help='Play track from cached search', type=int)
@click.option('-h', '--host', help='Network host')
# https://www.iana.org/assignments/service-names-port-numbers\
#        /service-names-port-numbers.xhtml
@click.option('-p', '--port', help='Network port',
              type=click.IntRange(1024, 49151))
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
                await click_echof(f'<blue>{song}<reset>')
            else:
                album_name = f'<blue>{song.parent.name}<yellow> / '
                song_name = f'<blue>{song.name}<reset>'
                await click_echof(album_name + song_name)
            async with await ffmpeg.stream(str(song)) as src:
                await StreamIO(src, out).flow()


async def barton_hall(audio_dest):
    """1977-05-08, Set 2 :-) ."""
    await click_echof(
        '<red>If you get confused, just listen to the music play.'
    )
    await click_echof('<white>¤<blue>__<red>¤ <blue>Robert Hunter<reset>')
    music = ''.join([
        'http://archive.org/download/',
        'gd1977-05-08.shure57.stevenson.29303.flac16/',
        'gd1977-05-08d02t0{track}.flac'
    ])

    # ... put this in a fixture or something ...
    out = None
    if audio_dest == 'speakers':
        out = sox.play()
    elif audio_dest == 'udp':
        out = ffmpeg.udp()
    else:
        # Check for file output.
        out_path = trio.Path(audio_dest)
        if audio_dest == '/dev/null':
            out = NullDestStream()
        elif await out_path.is_file() or await out_path.is_dir():
            out = ffmpeg.to_file(out_path)

    async with out:
        for num in range(4, 7):
            uri = music.format(track=num)
            await click_echof(f'<yellow>{uri}<reset>')
            async with await ffmpeg.stream(uri) as src:
                while True:
                    chunk = await src.receive_some(4096)
                    if not chunk:
                        break
                    await out.send_all(chunk)


if __name__ == '__main__':
    trio.run(main())
