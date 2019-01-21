"""Some commonly used test fixtures."""
import os

# import numpy as np
import pytest

# from reel.proc import Source


def set_env(env):
    """Add some variables to the environment."""
    for key in env:
        os.environ[key] = env[key]


def unset_env(env):
    """Remove some variables from the environment."""
    for key in env:
        del os.environ[key]


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
