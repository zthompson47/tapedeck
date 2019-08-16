"""Tapedeck finds and plays music across muiltiple sources and devices."""
import pkg_resources as _pkg
__version__ = "0.0.5"  # _pkg.get_distribution(__name__).version

from . import cli
