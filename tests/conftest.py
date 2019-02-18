"""Magic startup file for pytest.

Imported before tests.  Loads fixtures and sets environment
variables for subprocess testing.

"""
import logging
import os
from tempfile import mkdtemp

import pytest
import trio

import reel
from reel import Reel
from reel.cmd import ffmpeg, sox

# Log debug messages for testing.
LOG_DIR = trio.run(reel.config.get_xdg_data_dir, 'reel')
LOG_FILE = LOG_DIR / 'tests.log'
logging.basicConfig(filename=LOG_FILE, level='DEBUG')
LOGGER = logging.getLogger(__name__)
LOGGER.debug('<~~~~~~(~<~(o~>)~>~~~~~> BEGIN REEL TESTS LOGGING')

# Remove existing config vars except for testing.
for _env_key in os.environ.keys():
    if _env_key.startswith('REEL_'):
        if not _env_key.startswith('REEL_TESTS_'):
            del os.environ[_env_key]

# Create home directories for testing.
XDG = {
    'XDG_CONFIG_HOME': reel.Path(mkdtemp('xdg_config')),
    'XDG_CACHE_HOME': reel.Path(mkdtemp('xdg_cache')),
    'XDG_DATA_HOME': reel.Path(mkdtemp('xdg_data')),
    'XDG_RUNTIME_DIR': reel.Path(mkdtemp('xdg_runtime')),
}

# Set xdg environment variables.
for _key, _val in XDG.items():
    os.environ[_key] = _val

# Enable full test coverage for subprocesses.
os.environ['COVERAGE_PROCESS_START'] = 'setup.cfg'
os.environ['PYTHONPATH'] = '.'  # to find sitecustomize.py


def set_env(env):
    """Add some variables to the environment."""
    for key in env:
        os.environ[key] = env[key]


def unset_env(env):
    """Remove some variables from the environment."""
    for key in env:
        del os.environ[key]


@pytest.fixture
def neil_reel():
    """Return an audio stream of a short intro split into many files."""
    return Reel([ffmpeg.read(track) for track in [
        '/Users/zach/out000.wav', '/Users/zach/out001.wav',
        '/Users/zach/out002.wav', '/Users/zach/out003.wav',
        '/Users/zach/out004.wav', '/Users/zach/out005.wav',
    ]])


@pytest.fixture
def audio_dest():
    """Return an audio connection factory."""
    def audio_dest_fn():
        dest = os.environ.get('REEL_TESTS_AUDIO_DEST', '/dev/null')
        out = None
        if dest == 'speakers':
            out = sox.speakers()
        elif dest == 'udp':
            out = ffmpeg.to_udp('127.0.0.1', '9876')
        else:
            # Check for file output.
            out_path = reel.Path(dest)
            if (dest == '/dev/null' or
                    trio.run(out_path.is_file) or
                    trio.run(out_path.is_dir)):
                out = ffmpeg.to_file(out_path)
        return out
    return audio_dest_fn


@pytest.fixture(params=['python -m reel.cli', 'reel'])
def cli_cmd(request):
    """."""
    return request.param


@pytest.fixture
def audio_uri():
    """Provide some handy audio file locations."""
    return {
        'RADIO': 'http://ice1.somafm.com/groovesalad-256-mp3',
        'SONG': ''.join([
            'https://archive.org/download/',
            'gd1977-05-08.shure57.stevenson.29303.flac16/',
            'gd1977-05-08d02t04.flac'
        ])
    }


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
        port='8666',
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
