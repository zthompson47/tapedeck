"""Magic startup file for pytest.

Imported before tests.  Loads fixtures and sets environment
variables for subprocess testing.

"""
import logging
import os
from tempfile import mkdtemp

import pytest

import tapedeck

# Use config from environ for logging.
logging.basicConfig(
    filename=tapedeck.LOGGING_FILE,
    level=tapedeck.LOGGING_LEVEL
)

# Enable full test coverage for subprocesses.
os.environ['COVERAGE_PROCESS_START'] = 'setup.cfg'
os.environ['PYTHONPATH'] = '.'  # to find sitecustomize.py

# Create temp home directories.
os.environ['XDG_CONFIG_HOME'] = mkdtemp('xdg_config')
os.environ['XDG_CACHE_HOME'] = mkdtemp('xdg_cache')
os.environ['XDG_DATA_HOME'] = mkdtemp('xdg_data')
os.environ['XDG_RUNTIME_DIR'] = mkdtemp('xdg_runtime')


@pytest.fixture
def uri():
    """Return a list of music to play."""
    return type('Z', (object,), {
        'RADIO': 'http://ice1.somafm.com/groovesalad-256-mp3',
    })


@pytest.fixture
def env_audio_dest():
    """Enable setting an audio output for testing."""
    return os.environ.get('TAPEDECK_TESTING_AUDIO_DEST', '/dev/null')


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
