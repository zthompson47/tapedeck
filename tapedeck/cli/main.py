"""Command line interface to ``tapedeck``."""
import logging
import sys

import blessings
import trio
import trio_click as click

import tapedeck
from . import play, search

LOG_LEVEL = trio.run(tapedeck.config.env, 'TAPEDECK_LOG_LEVEL')
if LOG_LEVEL:
    LOG_FILE = trio.run(tapedeck.config.logfile, 'tapedeck.log')
    logging.basicConfig(level=LOG_LEVEL, filename=LOG_FILE)
LOGGER = logging.getLogger(__name__)
LOGGER.debug('Begin logging for tapedeck ~-~=~-~=~-~=~!!<(o>)!!~=~-~=~-~=~')

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
@click.option('--log-to-stderr', is_flag=True, help='Route logging to stderr')
async def tapedeck_cli(config, version, log_to_stderr):
    """Run the tapedeck cli."""
    if log_to_stderr:
        LOGGER.addHandler(logging.StreamHandler(sys.stderr))

    if version:
        LOGGER.debug('Running tapedeck v%s cli...', tapedeck.__version__)
        click.echo(f'{T.blue}¤_tapedeck_¤ ', nl=False)
        click.echo(f'{T.yellow}v{tapedeck.__version__}{T.normal}')

    if config:
        for key, val in (await tapedeck.config.env()).items():
            click.echo(f'{T.blue}{key}{T.normal}={T.yellow}{val}{T.normal}')


tapedeck_cli.add_command(play.play)
tapedeck_cli.add_command(search.search)

if __name__ == '__main__':
    tapedeck_cli()  # pylint: disable=no-value-for-parameter
