"""Some commonly used test fixtures."""
import logging
import os

# import numpy as np
import pytest

import reel
# from reel.proc import Source

ENV_COVERAGE = {
    'COVERAGE_PROCESS_START': 'setup.cfg',
    'PYTHONPATH': '.'
}

RADIO = 'http://ice1.somafm.com/groovesalad-256-mp3'

SONG = ''.join([
    'https://archive.org/download/',
    'gd1977-05-08.shure57.stevenson.29303.flac16/',
    'gd1977-05-08d02t04.flac'
])

logging.basicConfig(
    filename=reel.LOGGING_FILE,
    level=reel.LOGGING_LEVEL
)


def set_env(env):
    """Add some variables to the environment."""
    for key in env:
        os.environ[key] = env[key]


def unset_env(env):
    """Remove some variables from the environment."""
    for key in env:
        del os.environ[key]


@pytest.fixture
def env_audio_dest():
    """Enable setting an audio output for testing."""
    return os.environ.get('REEL_TESTING_AUDIO_DEST', '/dev/null')


@pytest.fixture(scope="session")
def env_home(tmp_path_factory):
    """Create an xdg environment with usable home directories."""
    return {
        'XDG_CONFIG_HOME': str(tmp_path_factory.mktemp('xdg_config')),
        'XDG_CACHE_HOME': str(tmp_path_factory.mktemp('xdg_cache')),
        'XDG_DATA_HOME': str(tmp_path_factory.mktemp('xdg_data')),
        'XDG_RUNTIME_DIR': str(tmp_path_factory.mktemp('xdg_runtime')),
    }


@pytest.fixture(scope="session")
def config_icecast(tmp_path_factory):
    """Return variables to populate an icecast.xml config file."""
    return dict(
        location='Neptune',
        admin_email='sushi@trident.sea',
        password='hack-it-up',
        hostname='127.0.0.1',
        port='8555',
        logdir=str(tmp_path_factory.mktemp('icecast_log')),
    )


@pytest.fixture(scope="function")
def audio_dir(tmp_path_factory):
    """Create a directory with different types of audio files."""
    rootdir = tmp_path_factory.mktemp('audio_dir')
    # output_wav = np.cos(2 * np.pi * 440 * np.arange(0, 5, 1 / 44100))
    # ... save the file ...
    # output_flac = Source('flac output.wav')
    return rootdir


@pytest.fixture
def music_dir(tmpdir):
    """Create a temporary directory with of music subdirectories."""
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
