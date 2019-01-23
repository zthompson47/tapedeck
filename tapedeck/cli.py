# pylint: disable=C0411
"""Command line interface for tapedeck."""
import trio
import trio_click as click

from reel.cmd import ffmpeg, sox
from reel.io import StreamIO

import tapedeck
from tapedeck.search import find_tunes


@click.group(invoke_without_command=True,
             context_settings=dict(help_option_names=['-h', '--help']),
             options_metavar='<options>')
@click.option('--cornell', help='Raise the roof.', metavar='<int>')
@click.option('-v', '--version', is_flag=True,
              help=f'Print "{tapedeck.__version__}" and exit.')
async def main(version, cornell):
    """¤ Manage your music."""
    await trio.sleep(0.1)
    if version:
        click.echo(tapedeck.__version__)
    if cornell and cornell == '77':
        await barton_hall()


@main.command(options_metavar='<options>')
@click.argument('directory', metavar='<directory>')
@click.option('-d', '--follow-dots', is_flag=True,
              help='Search hidden dot-directories.')
@click.option('-l', '--follow-links', is_flag=True,
              help='Search symlinked directories.')
async def search(directory, follow_links, follow_dots):
    """¤ Find your music."""
    results = find_tunes(directory,
                         followlinks=follow_links,
                         followdots=follow_dots)
    for folder in results:
        click.echo(folder.path)


@main.command(options_metavar='<options>')
@click.argument('music_uri', metavar='<music_uri>')
@click.option('-o', '--output-destination', default='speaker',
              help='Output destination')
async def play(music_uri, output_destination):
    """¤ Play your music."""
    destinations = {'speaker': sox.play,
                    'udp': ffmpeg.udp}
    click.echo(f'Playing {music_uri}')
    async with await destinations[str(output_destination)]() as out:
        async with await ffmpeg.stream(music_uri) as src:
            await StreamIO(src, out).flow()


async def barton_hall():
    """1977-05-08, Set 2 :-) ."""
    click.echo('''If you get confused,
                  just listen to the music play.
                  -- Rober Hunter''')
    music = ''.join(['https://archive.org/download/',
                     'gd1977-05-08.shure57.stevenson.29303.flac16/',
                     'gd1977-05-08d02t0{track}.flac'])
    async with await sox.play() as out:
        for num in range(4, 10):
            uri = music.format(track=num)
            click.echo(uri)
            async with await ffmpeg.stream(uri) as src:
                while True:
                    chunk = await src.receive_some(4096)
                    if not chunk:
                        break
                    await out.send_all(chunk)


if __name__ == '__main__':
    trio.run(main())  # pylint: disable=E1120
