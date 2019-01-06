"""The runtime configuration environment.

The config module reads settings from environment variables and
assigns defaults when appropriate.

"""
from os import environ as env
from pathlib import Path

HOME = Path.home()

# Application filesystem storage per XDG Base Directory Specification:
# https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
XDG_CONFIG_HOME = Path(env.get('XDG_CONFIG_HOME', '~/.config')).expanduser()
XDG_CACHE_HOME = Path(env.get('XDG_CACHE_HOME', '~/.cache')).expanduser()
XDG_DATA_HOME = Path(env.get('XDG_DATA_HOME', '~/.local/share')).expanduser()

# TODO warning message if no runtime dir, per xdg spec pylint: disable=W0511
XDG_RUNTIME_DIR = Path(env.get('XDG_RUNTIME_DIR', '~/.local/run')).expanduser()

# -- Application Configuration --

BLOCK_SIZE = int(env.get('TD_BLOCK_SIZE', 4096))
DSN = env.get('TD_DSN', 'postgresql://localhost/tapedeck')
SEARCH_PATH = env.get('TD_SEARCH_PATH', Path.home())
