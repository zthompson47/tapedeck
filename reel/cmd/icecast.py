"""The icecast streaming server."""
from .._daemon import Daemon
from .._spool import Spool


class Icecast(Daemon):
    """An icecast client and server."""

    _command = 'icecast'
    _config_base = 'icecast.xml'
    _config = dict(
        location='Neptune',
        admin_email='sushi@trident.sea',
        password='hack-it-up',
        hostname='127.0.0.1',
        port='8777',
    )

    async def _prepare(self, config):
        """Get the configuration file ready."""
        self._command.extend(['-c', str(config)])

    @classmethod
    def client(cls, mount):
        """Return a process that streams to the icecast server."""
        cmd = 'ffmpeg'
        uri = 'icecast://source:{}@{}:{}/{}'.format(
            cls._config['password'],
            cls._config['hostname'],
            cls._config['port'],
            mount
        )
        # Maybe:
        # -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 \
        # -reconnect_delay_max 2000
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
            uri
        ]
        return Spool(cmd, xflags=flags)
