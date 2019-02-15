"""This is reel."""
# import logging
import pkg_resources as _pkg

from . import cmd
from . import config
from . _path import Path
from . _spool import Spool
from . _reel import Reel
from . _transport import Transport

__version__ = _pkg.get_distribution(__name__).version
