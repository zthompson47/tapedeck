"""This is reel."""
import logging
import os

import trio

from reel.config import get_xdg_config_dir

__all__ = ['io', 'proc', 'tools']
__version__ = '0.0.2'

LOGGING_LEVEL = os.environ.get('REEL_LOGGING_LEVEL', 'DEBUG')
LOGGING_FILE = os.environ.get(
    'REEL_LOGGING_DIR',
    trio.run(get_xdg_config_dir) / 'reel.log'
)
logging.basicConfig(filename=LOGGING_FILE, level=LOGGING_LEVEL)