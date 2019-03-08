"""The ``tapedeck`` cli 'play' command."""
import argparse
import logging
import random
import sys
import termios

import trio
from trio import Lock, Path

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


async def folders_from_args(args):
    """Return a list of folders to play."""
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


async def playlist_from_args(args):
    """Return a list of tracks to play."""
    playlist = []
    folders = await folders_from_args(args)

    # Command line argument
    if args.track and await Path(args.track).is_file():
        playlist.append(Path(args.track))

    # Expand folders into songs
    for folder in folders:
        playlist += await scan_folder(folder)

    # Shuffle the playlist
    if args.shuffle:
        random.shuffle(playlist)

    return playlist


def validate(args):
    """Validate the command line arguments."""
    if args.output == 'udp':
        if args.host is None or args.port is None:
            raise argparse.ArgumentTypeError('-o', 'udp needs host and port')


async def play(args):
    """Build a playlist and play it."""
    validate(args)

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

    # Create the playlist.
    playlist = Reel(
        [ffmpeg.read(track) for track in await playlist_from_args(args)],
        announce_to=print
    )

    lock = Lock()

    async with await icecast.server() as icey:
        async with trio.open_nursery() as nursery:
            icey.start_daemon(nursery)

            # Play the playlist!
            async with playlist | destination as transport:
                transport.start_daemon(nursery)
                try:
                    async with Keyboard() as keyboard:
                        async for key in keyboard:
                            if key == 'q':
                                nursery.cancel_scope.cancel()
                            elif key == 'j':
                                # pylint: disable=not-async-context-manager
                                async with lock:
                                    await playlist.skip_to_next_track(
                                        close=True
                                    )
                except termios.error:
                    await transport.wait()
                await transport.stop()

            await icey.stop()

    return 0


def enter():
    """Entry point for setuptools console_scripts."""
    tdplay = argparse.ArgumentParser()
    load_args(tdplay)
    args = tdplay.parse_args()
    sys.exit(trio.run(play, args))


if __name__ == '__main__':
    enter()
