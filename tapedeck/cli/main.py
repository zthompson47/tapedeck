"""Command line interface to ``tapedeck``."""
import logging
import sys

import trio
import trio_click as click

import tapedeck
from . import play, search
from .. import config

LOG_LEVEL = trio.run(config.env, 'TAPEDECK_LOG_LEVEL')
if LOG_LEVEL:
    LOG_FILE = trio.run(config.logfile, 'tapedeck.log')
    logging.basicConfig(level=LOG_LEVEL, filename=LOG_FILE)
LOGGER = logging.getLogger(__name__)
LOGGER.debug('Begin logging for tapedeck ~-~=~-~=~-~=~!!<(o>)!!~=~-~=~-~=~')


@click.group(invoke_without_command=True,
             context_settings=dict(help_option_names=['--help']),
             options_metavar='[options]',
             name='asdf',
             help='''¤_ Tapedeck _¤

                     Play your music across a variety of
                     sources and destinations.  Share torrents
                     and stream live music.  It's like a fresh
                     box of blank tapes.
                  ''')
@click.option('--log-to-stderr', is_flag=True, help='Print logging to stderr')
@click.option('--config', is_flag=True, help='Print the configuration')
@click.option('--version', is_flag=True, help='Print version number and exit')
@click.help_option('--help', help='Display help message and exit')
async def tapedeck_cli(**kwargs: str) -> None:
    """Run the tapedeck cli."""
    if kwargs['log_to_stderr']:
        LOGGER.addHandler(logging.StreamHandler(sys.stderr))

    if kwargs['version']:
        LOGGER.debug('Running tapedeck v%s cli...', tapedeck.__version__)
        click.echo('v' + tapedeck.__version__)

    if kwargs['config']:
        for key, val in (await tapedeck.config.env()).items():
            if not val:
                val = ''
            click.echo(f'{key}={val}')


tapedeck_cli.add_command(play.play)
tapedeck_cli.add_command(search.search)

if __name__ == '__main__':
    tapedeck_cli()  # pylint: disable=no-value-for-parameter
