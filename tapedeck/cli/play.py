"""The ``tapedeck`` cli 'play' command."""
import logging
import random
import sys

import blessings
import trio

import reel
from reel.config import (
    get_xdg_cache_dir, get_xdg_config_dir, get_xdg_data_dir, get_config
)
from reel.cmd import ffmpeg, sox

import tapedeck
from tapedeck.search import find_tunes, is_audio

LOG_LEVEL = trio.run(tapedeck.config.env, 'TAPEDECK_LOG_LEVEL')
if LOG_LEVEL:
    LOG_FILE = trio.run(tapedeck.config.logfile, 'tapedeck.log')
    logging.basicConfig(level=LOG_LEVEL, filename=LOG_FILE)
LOG = logging.getLogger(__name__)
LOG.addHandler(logging.StreamHandler(sys.stderr))

T = blessings.Terminal()

PORTS = range(8771, 8777)


# pylint: disable=too-many-locals, too-many-branches
async def play(args):
    """Build a playlist and play it."""
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
    if args.output == 'speakers':
        out = sox.speakers()
    elif args.output == 'udp':
        if args.host is None or args.port is None:
            raise Exception('-o', 'udp needs host and port')
        out = ffmpeg.to_udp(host=args.host, port=args.port)
    elif args.output == 'icecast':
        out = ffmpeg.to_icecast(
            host='127.0.0.1',
            port='8777',
            mount='asdf',
            password='hack-it-up'
        )
    else:
        # Check for file output.
        out_path = reel.Path(args.output)
        if (args.output == '/dev/null' or
                await out_path.is_file() or
                await out_path.is_dir()):
            out = ffmpeg.to_file(out_path)

    # Create the playlist.
    plst = reel.Reel(
        [ffmpeg.read(track) for track in playlist],
        announce_to=print
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
    async with reel.Spool('icecast', xflags=flags) as icecast:
        async with trio.open_nursery() as nursery:
            icecast.start_daemon(nursery)

            # Play the playlist!
            async with plst | out as transport:
                await transport.play()
            await icecast.stop()
