"""Tapedeck finds and plays music across muiltiple sources and devices."""
import pkg_resources as _pkg
__version__ = _pkg.get_distribution(__name__).version

from .config import logfile
from . import cli
