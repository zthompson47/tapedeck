# pylint: disable=too-many-statements, broad-except
"""The ``tapedeck`` cli 'play' command."""
import argparse
import logging
import random
import sys
import termios

import blessings
import trio

import kbhit
import reel
from reel.config import (
    get_xdg_cache_dir, get_xdg_config_dir, get_xdg_data_dir, get_config
)
from reel.cmd import ffmpeg, sox

import tapedeck.config
from tapedeck.search import find_tunes, is_audio

LOG_LEVEL = trio.run(tapedeck.config.env, 'TAPEDECK_LOG_LEVEL')
if LOG_LEVEL:
    LOG_FILE = trio.run(tapedeck.config.logfile, 'tapedeck.log')
    logging.basicConfig(
        level=LOG_LEVEL,
        filename=LOG_FILE,
        format='%(process)d:%(levelname)s:%(module)s:%(message)s'
    )
LOG = logging.getLogger(__name__)
# LOG.addHandler(logging.StreamHandler(sys.stderr))
LOG.debug('[o_ NOW LOGGING tapedeck.cli.play _o]')

T = blessings.Terminal()

PORTS = range(8771, 8777)


def load_args(tdplay):
    """Parse arguments for the ``tapedeck play`` subcomand."""
    # o=~ tdplay ~=o
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


# pylint: disable=too-many-locals, too-many-branches
async def play(args):
    """Build a playlist and play it."""
    LOG.debug('[o_ TAPEDECK cli.play _o]')
    playlist = []

    if args.memory:
        # Find the track filename by index in the cached search results.
        cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
        async with await cache_file.open('r') as out:
            lines = (await out.read()).split('\n')[0:-1]
        track = lines[int(args.memory) - 1]
        music_path = reel.Path(track[track.find(' ') + 1:])
    else:
        music_path = reel.Path(args.track)

    if await reel.Path(music_path).is_dir():
        playlist_folders = [music_path]
        if args.recursive:
            # Run find_tunes on this dir to get all music folders.
            results = await find_tunes(music_path)
            for folder in results:
                playlist_folders.append(reel.Path(folder.path))

        # in a directory, queue each song file
        for folder in playlist_folders:
            songs = [_ for _ in await folder.iterdir() if _.is_file()]
            songs.sort()
            for song in songs:
                if is_audio(str(song)):
                    playlist.append(song)
    else:
        # Otherwise, just queue the uri.
        playlist.append(args.track)

    # Shuffle the playlist.
    if args.shuffle:
        random.shuffle(playlist)  # ... tests needed ...

    # Choose the output.
    out = None
    needs_icecast = False
    if args.output == 'speakers':
        out = sox.speakers()
    elif args.output == 'udp':
        if args.host is None or args.port is None:
            raise Exception('-o', 'udp needs host and port')
        out = ffmpeg.to_udp(host=args.host, port=args.port)
    elif args.output == 'icecast':
        needs_icecast = True
        out = ffmpeg.to_icecast(
            host='127.0.0.1',
            port='8777',
            mount='asdf',
            password='hack-it-up'
        )
    else:
        # Check for file output.
        out_path = reel.Path(args.output)
        LOG.debug('///////!!!!++++++++++++/////>>> %s ', str(out_path))
        # if (args.output == '/dev/null' or
        #         await out_path.is_file() or
        #         await out_path.is_dir()):
        out = ffmpeg.to_file(out_path)

    def announcer(message):
        """Receive messages and print them."""
        LOG.debug('ANNOUNCER-MESSAGE >>>>!!>> %s', message)
        print(message)

    # Create the playlist.
    plst = reel.Reel(
        [ffmpeg.read(track) for track in playlist],
        announce_to=announcer
    )

    # Start an icecast daemon.
    config_icecast = dict(
        location='Neptune',
        admin_email='sushi@trident.sea',
        password='hack-it-up',
        hostname='127.0.0.1',
        port='8777',
        logdir=str(await get_xdg_data_dir()),
    )
    config_dir = await get_xdg_config_dir()
    config = await get_config(config_dir, 'icecast.xml', **config_icecast)
    flags = ['-c', str(config)]
    LOG.debug(flags)
    lock = trio.Lock()
    async with reel.Spool('icecast', xflags=flags) as icecast:
        async with trio.open_nursery() as nursery:
            if needs_icecast:
                icecast.start_daemon(nursery)

            # Play the playlist!
            async with plst | out as transport:
                done_evt = transport.start_daemon(nursery)
                LOG.debug('___ started transport')

                try:
                    keyboard = kbhit.KBHit()
                    while True:
                        if done_evt.is_set():
                            break
                        if keyboard.kbhit():
                            char = keyboard.getch()
                            if ord(char) == ord('q'):
                                break
                            if ord(char) == ord('j'):
                                # pylint: disable=not-async-context-manager
                                async with lock:
                                    await plst.skip_to_next_track(close=True)
                        await trio.sleep(0.01)
                    await transport.stop()
                    keyboard.set_normal_term()
                except termios.error:
                    while not done_evt.is_set():
                        await trio.sleep(0.01)

                LOG.debug('___ stopping transport')
                await transport.stop()
                LOG.debug('___ stopped transport')

            LOG.debug('___ stopping icecast')
            if needs_icecast:
                await icecast.stop()
            LOG.debug('___ stopped icecast')
            LOG.debug('nursery: %s', nursery.child_tasks)
        LOG.debug('___ out of nursery!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1')
    return 0


def enter():
    """Entry point for setuptools console_scripts."""
    LOG.debug('[o_o] enter')
    tdplay = argparse.ArgumentParser()
    load_args(tdplay)
    args = tdplay.parse_args()
    try:
        sys.exit(trio.run(play, args))
    except trio.ClosedResourceError as err:
        LOG.exception(err)


if __name__ == '__main__':
    LOG.debug('[o_o] __main__')
    enter()
