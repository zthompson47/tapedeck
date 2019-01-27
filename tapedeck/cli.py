"""The command line interface to tapedeck."""
import random

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
    options_metavar='<options>'
)
@click.option('--cornell', help='Raise the roof.', metavar='<int>')
@click.option(
    '-o', '--output-destination',
    default='speakers',
    help='Output destination'
)
@click.option(
    '-v', '--version', is_flag=True,
    help=f'Print "{tapedeck.__version__}" and exit.'
)
async def main(version, cornell, output_destination):
    """¤ Manage your music."""
    await trio.sleep(0.1)
    if version:
        await click_echof(tapedeck.__version__)
    if cornell and cornell == '77':
        await barton_hall(output_destination)


@main.command(options_metavar='<options>')
@click.argument('directory', metavar='<directory>', required=False)
@click.option(
    '-d', '--follow-dots', is_flag=True,
    help='Search hidden dot-directories.'
)
@click.option(
    '-h', '--history', is_flag=True,
    help='Show search history'
)
@click.option(
    '-l', '--follow-links', is_flag=True,
    help='Search symlinked directories.'
)
async def search(directory, follow_links, follow_dots, history):
    """Find your music."""
    if history:
        cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
        async with await cache_file.open('r') as out:
            lines = (await out.read()).split('\n')[0:-1]
        output = []
        for line in lines:
            number = line[0:line.find(' ')]
            filename = line[line.find(' ') + 1:]
            path = trio.Path(filename)
            output.append(number + ' ' + path.name)
        click.echo_via_pager('\n'.join(output))
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
        await click_echof(f'<green>{idx}. <blue>{path.name}<reset>')

    # Store results in a cache file.
    cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
    async with await cache_file.open('w') as out:
        idx = 0
        for folder in results:
            idx += 1
            await out.write(f'{idx}. {str(folder.path)}\n')


# pylint: disable=too-many-branches,too-many-locals
@main.command(options_metavar='<options>')  # noqa: C901
@click.argument('music_uri', metavar='<music_uri>', required=False)
@click.option(
    '-o', '--output-destination',
    default='speakers',
    help='Output destination'
)
@click.option(
    '-h', '--history',
    help='Play track from search history'
)
@click.option(
    '-s', '--shuffle', is_flag=True,
    help='Shuffle order of tracks'
)
async def play(music_uri, output_destination, history, shuffle):
    """Play your music."""
    playlist = []
    if history:
        cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
        async with await cache_file.open('r') as out:
            lines = (await out.read()).split('\n')[0:-1]
        track = lines[int(history) - 1]
        music_path = trio.Path(track[track.find(' ') + 1:])
    else:
        music_path = trio.Path(music_uri)

    # queue music_uri
    if await trio.Path(music_path).is_dir():
        # in a directory, queue each song file
        songs = [_ for _ in await music_path.iterdir() if await _.is_file()]
        songs.sort()
        for song in songs:
            if is_audio(str(song)):
                playlist.append(await song.resolve())
    else:
        # Otherwise, just queue the uri.
        playlist.append(music_uri)

    out = None
    if output_destination == 'speakers':
        out = sox.play()
    elif output_destination == 'udp':
        out = ffmpeg.udp()
    else:
        # Check for file output.
        out_path = trio.Path(output_destination)
        if output_destination == '/dev/null':
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
