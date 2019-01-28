"""Tapedeck finds and plays music across muiltiple sources and devices."""
import os

import trio

from reel.config import get_xdg_config_dir
from . import cli  # noqa: F401

__version__ = '0.0.2'

LOGGING_LEVEL = os.environ.get(
    'TAPEDECK_LOGGING_LEVEL',
    'DEBUG'
).upper()
LOGGING_DIR = os.environ.get(
    'TAPEDECK_LOGGING_DIR',
    trio.run(get_xdg_config_dir, 'tapedeck')
)
LOGGING_FILE = os.environ.get(
    'TAPEDECK_LOGGING_FILE',
    str(trio.Path(LOGGING_DIR) / 'tapedeck.log')
)
