"""Test the application configuration system."""
from importlib import reload
import os
from pathlib import Path

from tapedeck import config


def test_xdg_environment_unset():
    """Default locations of configuration files are provided if
    the XDG_* environment variables are not set.

    """
    unset_env()
    assert config.HOME == Path.home()
    assert config.XDG_CONFIG_HOME == Path.home() / '.config'
    assert config.XDG_CACHE_HOME == Path.home() / '.cache'
    assert config.XDG_DATA_HOME == Path.home() / '.local' / 'share'
    assert config.XDG_RUNTIME_DIR == Path.home() / '.local' / 'run'

    # TODO log warning if no xdg_runtime pylint: disable=W0511


def test_xdg_environment_set():
    """XDG_* environment variables are used when they are set."""
    set_env()
    assert config.HOME == Path(TEST_ENV['HOME'])
    assert config.XDG_CONFIG_HOME == Path(TEST_ENV['XDG_CONFIG_HOME'])
    assert config.XDG_CACHE_HOME == Path(TEST_ENV['XDG_CACHE_HOME'])
    assert config.XDG_DATA_HOME == Path(TEST_ENV['XDG_DATA_HOME'])
    assert config.XDG_RUNTIME_DIR == Path(TEST_ENV['XDG_RUNTIME_DIR'])


def test_application_config():
    """Application settings are configured in environment variables."""
    set_env()
    assert config.BLOCK_SIZE == int(TEST_ENV['TD_BLOCK_SIZE'])
    assert config.DSN == TEST_ENV['TD_DSN']
    assert config.SEARCH_PATH == TEST_ENV['TD_SEARCH_PATH']


# Fixtures

TEST_ENV = {
    'HOME': 'home',
    'XDG_CONFIG_HOME': 'xdg_config',
    'XDG_CACHE_HOME': 'xdg_cache',
    'XDG_DATA_HOME': 'xdg_data',
    'XDG_RUNTIME_DIR': 'xdg_runtime',
    'TD_BLOCK_SIZE': '4096',
    'TD_DSN': 'postgresql://localhost/tapedeck',
    'TD_SEARCH_PATH': 'postgresql://localhost/tapedeck',
}


def unset_env():
    """Clear the test environment for the tapedeck.config module."""
    for key in TEST_ENV:
        os.unsetenv(key)
    reload(config)


def set_env():
    """Load the test environment for the tapedeck.config module."""
    for key in TEST_ENV:
        os.environ[key] = TEST_ENV[key]
    reload(config)
