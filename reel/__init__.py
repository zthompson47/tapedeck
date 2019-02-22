"""This is reel."""
import pkg_resources as _pkg
__version__ = _pkg.get_distribution(__name__).version

from . import cmd
from . import config
from ._path import Path
from ._reel import Reel
from ._spool import Spool
from ._track import Track
from ._streamer import Streamer
from ._transport import Transport
