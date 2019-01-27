"""This is reel."""
import os

import trio

from reel.config import get_xdg_config_dir

__all__ = ['cmd', 'io', 'proc', 'tools']
__version__ = '0.0.4'

LOGGING_LEVEL = os.environ.get(
    'REEL_LOGGING_LEVEL',
    'debug'
).upper()
LOGGING_DIR = os.environ.get(
    'REEL_LOGGING_DIR',
    trio.run(get_xdg_config_dir)
)
LOGGING_FILE = os.environ.get(
    'REEL_LOGGING_FILE',
    str(trio.Path(LOGGING_DIR) / 'reel.log')
)
