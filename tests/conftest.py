"""Magic startup file for pytest.

Imported before tests.  Loads fixtures and sets environment
variables for subprocess testing.

"""
import logging
import os
from tempfile import mkdtemp

import pytest
import trio

from reel import Path

import tapedeck


# Log debug messages for testing.
LOG_FILE = trio.run(tapedeck.logfile, 'tests.log')
logging.basicConfig(filename=LOG_FILE, level='DEBUG')
LOGGER = logging.getLogger(__name__)
LOGGER.debug('Begin logging for tests ~-~=~-~=~-~=~!!((o))!!~=~-~=~-~=~')

# Fetch testing configuration from environment vars.
TESTING_AUDIO_DEST = os.environ.get('TAPEDECK_TESTING_AUDIO_DEST', '/dev/null')

# Remove any existing TAPEDECK_* config vars.
for key in os.environ.keys():
    if key.startswith('TAPEDECK_'):
        del os.environ[key]

# Create home directories for testing.
XDG = {
    'XDG_CONFIG_HOME': Path(mkdtemp('xdg_config')),
    'XDG_CACHE_HOME': Path(mkdtemp('xdg_cache')),
    'XDG_DATA_HOME': Path(mkdtemp('xdg_data')),
    'XDG_RUNTIME_DIR': Path(mkdtemp('xdg_runtime')),
}

# Set xdg environment variables.
for key, val in XDG.items():
    os.environ[key] = val

# Enable full test coverage for subprocesses.
os.environ['COVERAGE_PROCESS_START'] = 'setup.cfg'
os.environ['PYTHONPATH'] = '.'  # to find sitecustomize.py


@pytest.fixture
def xdg():
    """Return the xdg environment."""
    return XDG


@pytest.fixture
def uri():
    """Return a list of music to play."""
    return type('Z', (object,), {
        'RADIO': 'http://ice1.somafm.com/groovesalad-256-mp3',
    })


@pytest.fixture
def env_audio_dest():
    """Enable setting an audio output for testing."""
    return TESTING_AUDIO_DEST


@pytest.fixture
def music_dir(tmpdir):
    """Create a temporary directory with subdirectories of music."""
    music_dirs = [
        {
            'root1': [
                {'Some folder.shnf': ['asdf.wav']},
                {'some other folder': ['rr.txt', 'asdf.wav', 'eHello~!.doc']},
                {'subdir': [
                    {'subsubdir': [
                        {'subsubsubdir': ['asdfasdfasdfasdf.aac']},
                    ]},
                    [],
                ]},
                [],
                'rootfile.txt',
                {'yeah whatev': []},
            ],
        },
    ]

    def create_nodes(structure, parent_node=None):
        """Create a filesystem from a template `structure`."""
        result = None
        for node in structure:
            if isinstance(node, dict):
                for subnode in node.keys():
                    if parent_node:
                        result = parent_node.join(subnode).mkdir()
                    else:
                        result = tmpdir.join(subnode).mkdir()
                    create_nodes(node[subnode], result)
            elif isinstance(node, list):
                for subnode in node:
                    create_nodes(subnode, parent_node)
            elif isinstance(node, str):
                if parent_node:
                    parent_node.join(node).write('yup')
        return result
    return str(create_nodes(music_dirs))
