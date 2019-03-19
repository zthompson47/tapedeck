"""The aria2 bittorrent client."""
from .._daemon import Daemon


class Aria2(Daemon):
    """An aria2 rpc process."""

    _command = 'aria2'
    _config_base = 'aria2.conf'
    _config = dict(
    )

    async def _prepare(self, config):
        """Get the configuration file ready."""
        assert config
