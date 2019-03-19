"""The redis storage engine."""
from .._daemon import Daemon


class Redis(Daemon):
    """A redis client and server."""

    _command = 'redis-server'
    _config_base = 'redis.conf'
    _config = dict(
        ipaddr='127.0.0.1',
        port='8776',
    )

    async def _prepare(self, config):
        """Get the configurate file ready."""
        self._command.append(str(config))
