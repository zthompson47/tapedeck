"""Command line interface for tapedeck."""
import logging

import trio
import trio_click as click

import reel

logging.basicConfig(filename=reel.LOGGING_FILE, level=reel.LOGGING_LEVEL)


@click.command()
@click.option('-v', '--version', is_flag=True,
              help='Print the version number and exit.')
@click.option('-c', '--config', is_flag=True,
              help='Print the configuration.')
async def main(**kwargs: str) -> None:
    """Run reel from the command line."""
    if kwargs['version']:
        click.echo(reel.__version__)
    if kwargs['config']:
        click.echo(f'REEL_LOGGING_DIR={reel.LOGGING_DIR}')
        click.echo(f'REEL_LOGGING_FILE={reel.LOGGING_FILE}')
        click.echo(f'REEL_LOGGING_LEVEL={reel.LOGGING_LEVEL}')

if __name__ == '__main__':
    trio.run(main())
