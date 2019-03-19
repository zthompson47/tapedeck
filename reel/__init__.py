"""This is reel."""
import pkg_resources as _pkg
__version__ = _pkg.get_distribution(__name__).version

from . import cmd
from . import config
from ._daemon import Daemon
from ._reel import Reel
from ._server import Server
from ._spool import Spool
from ._streamer import Streamer
from ._track import Track
from ._transport import Transport
