"""The Icecast streaming server."""
from reel.config import get_xdg_config_dir, get_xdg_data_dir, get_config

from .._spool import Spool


class IcecastServer(Spool):
    """An icecast client and server."""

    def __init__(self, command='icecast'):
        """Store the configuration for the server command."""
        self._config = dict(
            location='Neptune',
            admin_email='sushi@trident.sea',
            password='hack-it-up',
            hostname='127.0.0.1',
            port='8777',
            logdir='/Users/zach',
            # logdir=str(await get_xdg_data_dir()),
        )
        super().__init__(self, command)


async def server():
    """Return a command to run an icecast server."""
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
    return Spool('icecast', xflags=flags)


def client(host='127.0.0.1', port='8777', mount='asdf', password='hack-it-up'):
    """Return a command to send a stream to an icecast server."""
    cmd = 'ffmpeg'
    flags = [
        '-re',
        '-ac', '2',
        '-ar', '44.1k',
        '-f', 's16le',
        '-i', '-',
        '-vn',
        '-codec:a', 'libvorbis',
        '-q:a', '8.0',
        '-content_type', 'audio/ogg',
        '-f', 'ogg',
        f'icecast://source:{password}@{host}:{port}/{mount}'
    ]
    return Spool(cmd, xflags=flags)
