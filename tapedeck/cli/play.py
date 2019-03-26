"""The ``tapedeck`` cli 'play' command."""
import argparse
import logging
import random

import trio
# from trio_websocket import serve_websocket, ConnectionClosed

from reel import Reel
from reel.cmd import ffmpeg, sox, Icecast, Redis, Aria2
from reel.keyboard import Keyboard, KEY_RIGHT

from tapedeck.search import cached_search, find_tunes, scan_folder

LOG = logging.getLogger(__name__)


async def play(args, nursery):
    """Build a playlist and play it."""
    validate(args)

    playlist = await playlist_from_args(args)
    output = output_from_args(args)

    async with Aria2() | Icecast() | Redis() > nursery as server:
        async with playlist >> output as player:
            with player.spawn_in(nursery):
                async with Keyboard() as user:
                    async for key in user:

                        if key in ['l', KEY_RIGHT]:
                            await playlist.skip_to_next_track()

                        elif key == '?':
                            print(server, player)

                        elif key == 'q':
                            print('Quitting...')
                            break


def validate(args) -> None:
    """Validate the command line arguments."""
    if args.output == 'udp':
        if args.host is None or args.port is None:
            raise argparse.ArgumentTypeError('-o', 'udp needs host and port')


async def playlist_from_args(args) -> Reel:
    """Return a list of files to play."""
    playlist = []
    folders = await _folders_from_args(args)

    # Command line argument
    if args.track and not await trio.Path(args.track).is_dir():
        playlist.append(trio.Path(args.track))

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


def output_from_args(args):
    """Figure out where to send the audio."""
    outputs = {
        'speakers': sox.speakers(),
        'udp': ffmpeg.to_udp(host=args.host, port=args.port),
        'icecast': Icecast.client('asdf'),
        'default': ffmpeg.to_file(trio.Path(args.output))
    }

    try:
        output = outputs[args.output]
    except KeyError:
        output = outputs['default']
    return output


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
        for folder in await find_tunes(trio.Path(args.track)):
            folders.append(trio.Path(folder.path))

    # Command line argument
    if args.track and await trio.Path(args.track).is_dir():
        folders.append(trio.Path(args.track))

    return folders


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


async def main(args):
    """Launch main program tasks."""
    async with trio.open_nursery() as nursery:
        await play(args, nursery)


def enter():
    """Parse arguments and run.

    Used by setuptools as the entry point to ``tdplay``.

    """
    tdplay = argparse.ArgumentParser()
    load_args(tdplay)
    args = tdplay.parse_args()
    trio.run(main, args)


if __name__ == '__main__':
    enter()
