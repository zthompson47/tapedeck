"""Command line interface to ``tapedeck``."""
import trio_click as click

import tapedeck
from . import play, search


@click.group(invoke_without_command=True,
             context_settings=dict(help_option_names=['--help']),
             options_metavar='[options]',
             name='asdf',
             help='''¤_tapedeck_¤

                     Play your music across a variety of
                     sources and destinations.  Share torrents
                     and stream live music.  It's like a fresh
                     box of blank tapes.
                  ''')
@click.option('--version', is_flag=True, help='Print version number and exit')
@click.help_option('--help', help='Display help message and exit')
def tapedeck_cli(version: str) -> None:
    """Run the tapedeck cli."""
    if version:
        click.echo('v' + tapedeck.__version__)


tapedeck_cli.add_command(play.play)
tapedeck_cli.add_command(search.search)

if __name__ == '__main__':
    tapedeck_cli()  # pylint: disable=no-value-for-parameter
