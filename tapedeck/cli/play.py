"""The ``tapedeck`` cli 'play' command."""
import argparse
import logging
import random

import trio
from trio import Path

from reel import Reel
from reel.cmd import ffmpeg, icecast, sox
from reel.keyboard import Keyboard

from tapedeck.search import cached_search, find_tunes, scan_folder

LOG = logging.getLogger(__name__)


def load_args(tdplay):
    """Parse arguments for the ``tapedeck play`` subcomand."""
    tdplay.add_argument('track', metavar='TRACK', nargs='?')
    tdplay.add_argument(
        '-o', '--output', default='speakers',
        help='output destination'
    )
    tdplay.add_argument(
        '-s', '--shuffle', action='store_true', help='shuffle order of tracks'
    )
    tdplay.add_argument(
        '-r', '--recursive', action='store_true', help='play subfolders'
    )
    tdplay.add_argument(
        '-m', '--memory', metavar='MEMORY', type=int,
        help='play track number from last search'
    )
    tdplay.add_argument(
        '--host', type=str, help='network streaming host'
    )
    tdplay.add_argument(
        '--port', type=str, help='network streaming port'
    )
    tdplay.set_defaults(func=play)


def validate(args) -> None:
    """Validate the command line arguments."""
    if args.output == 'udp':
        if args.host is None or args.port is None:
            raise argparse.ArgumentTypeError('-o', 'udp needs host and port')


async def _folders_from_args(args):
    """Return a list of folders to play.

    Used by playlist_from_args.

    """
    folders = []

    # Get folder from cached search
    if args.memory:
        folders.append(await cached_search(args.memory))

    # Dig for more tracks
    if args.recursive:
        for folder in await find_tunes(Path(args.track)):
            folders.append(Path(folder.path))

    # Command line argument
    if args.track and await Path(args.track).is_dir():
        folders.append(Path(args.track))

    return folders


async def playlist_from_args(args) -> Reel:
    """Return a list of files to play."""
    playlist = []
    folders = await _folders_from_args(args)

    # Command line argument
    if args.track and await Path(args.track).is_file():
        playlist.append(Path(args.track))

    # Expand folders into songs
    for folder in folders:
        playlist += await scan_folder(folder)

    # Shuffle the playlist
    if args.shuffle:
        random.shuffle(playlist)

    return Reel(
        [ffmpeg.read(track) for track in playlist],
        announce_to=print
    )


def destination_from_args(args):
    """Figure out where to send the audio."""
    destinations = {
        'speakers': sox.speakers(),
        'udp': ffmpeg.to_udp(host=args.host, port=args.port),
        'icecast': icecast.client(),
        'default': ffmpeg.to_file(Path(args.output))
    }

    try:
        destination = destinations[args.output]
    except KeyError:
        destination = destinations['default']
    return destination


async def play(args):
    """Build a playlist and play it."""
    validate(args)

    playlist = await playlist_from_args(args)
    destination = destination_from_args(args)

    # Server
    async with trio.open_nursery() as nursery:
        async with await icecast.server() as ice:
            ice.spawn_in(nursery)
            async with playlist | destination as transport:
                with transport.spawn_in(nursery):

                    # Client
                    async with Keyboard() as user:
                        async for keypress in user:
                            if keypress == 'q':
                                nursery.cancel_scope.cancel()
                                # await transport.stop()
                            elif keypress == 'j':
                                # lock = trio.Lock()
                                # pylint: disable=not-async-context-manager
                                # async with lock:
                                await playlist.skip_to_next_track(close=True)
            await ice.stop()


def enter():
    """Parse arguments and run.

    Used by setuptools as the entry point to ``tdplay``.

    """
    tdplay = argparse.ArgumentParser()
    load_args(tdplay)
    args = tdplay.parse_args()
    try:
        trio.run(play, args)
    except trio.ClosedResourceError as error:
        LOG.exception(error)


if __name__ == '__main__':
    enter()
