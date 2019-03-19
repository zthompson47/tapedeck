"""The aria2 bittorrent client."""
from .._daemon import Daemon


class Aria2(Daemon):
    """An aria2 rpc process."""

    _command = 'aria2c --enable-rpc -d /Users/zach/Downloads'
