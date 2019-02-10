"""Command line interface to ``tapedeck``."""
import blessings
import trio_click as click

import tapedeck
from . import play, search

T = blessings.Terminal()


@click.group(invoke_without_command=True,
             context_settings=dict(help_option_names=['--help']),
             options_metavar='[options]',
             name='asdf',
             help=f'''{T.blue}¤_ {T.yellow}Tapedeck {T.blue}_¤{T.normal}

                     Play your music across a variety of
                     sources and destinations.  Share torrents
                     and stream live music.  It's like a fresh
                     box of blank tapes.
                  ''')
@click.help_option('--help', help='Display help message and exit')
@click.option('--config', is_flag=True, help='Print configuration and exit')
@click.option('--version', is_flag=True, help='Print version number and exit')
async def tapedeck_cli(config, version):
    """Run the tapedeck cli."""
    if version:
        click.echo(f'{T.blue}¤_tapedeck_¤ ', nl=False)
        click.echo(f'{T.yellow}v{tapedeck.__version__}{T.normal}')

    if config:
        for key, val in (await tapedeck.config.env()).items():
            click.echo(f'{T.blue}{key}{T.normal}={T.yellow}{val}{T.normal}')


tapedeck_cli.add_command(play.play)
tapedeck_cli.add_command(search.search)

if __name__ == '__main__':
    tapedeck_cli()  # pylint: disable=no-value-for-parameter
