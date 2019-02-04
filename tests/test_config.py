# pylint: disable=W0611, W0621
"""Test the application configuration system."""
import pathlib

import trio

from reel.config import (
    get_config,
    get_package_dir,
    get_package_name,
    get_xdg_cache_dir,
    get_xdg_config_dir,
    get_xdg_data_dir,
    get_xdg_runtime_dir,
    get_xdg_home,
)

from reel import Path

from .conftest import set_env, unset_env


async def test_fixture_env_home_works(env_home):
    """Make sure that the env_home fixture returns usable directories."""
    for var in ['XDG_CONFIG_HOME',
                'XDG_CACHE_HOME',
                'XDG_DATA_HOME',
                'XDG_RUNTIME_DIR']:
        assert await Path(env_home[var]).exists()


async def test_fixture_env_home_uses_environ(env_home):
    """Use XDG_* environment variables when they are set."""
    set_env(env_home)
    config = await get_xdg_home()
    assert config['XDG_CONFIG_HOME'] == env_home['XDG_CONFIG_HOME']
    assert config['XDG_CACHE_HOME'] == env_home['XDG_CACHE_HOME']
    assert config['XDG_DATA_HOME'] == env_home['XDG_DATA_HOME']
    assert config['XDG_RUNTIME_DIR'] == env_home['XDG_RUNTIME_DIR']


async def test_fixture_env_home_uses_default(env_home):
    """Provide xdg home directories if not set in the environemnt."""
    unset_env(env_home)
    config = await get_xdg_home()
    home = pathlib.Path.home()
    assert config['XDG_CONFIG_HOME'] == str(home / '.config')
    assert config['XDG_CACHE_HOME'] == str(home / '.cache')
    assert config['XDG_DATA_HOME'] == str(home / '.local' / 'share')
    assert config['XDG_RUNTIME_DIR'] == str(home / '.local' / 'run')
    # ... log warning if no xdg_runtime pylint : disable = W0511 ...


async def test_get_package_dir():
    """Get the path to this package."""
    assert await Path.canon('./reel') == str(await get_package_dir())


async def test_get_package_name():
    """Get the name of this package."""
    assert await get_package_name() == 'reel'


async def test_get_xdg_home(env_home):
    """Call get_xdg_home with various arguments."""
    set_env(env_home)
    config = await get_xdg_home()
    assert config['XDG_DATA_HOME'] == env_home['XDG_DATA_HOME']
    assert await get_xdg_home('XDG_DATA_HOME') == env_home['XDG_DATA_HOME']


async def test_get_xdg_config_dir(env_home):
    """Create a configuration directory for an app."""
    set_env(env_home)

    sub_dir = await get_xdg_config_dir('_testapp_', '_feature_')
    assert await sub_dir.exists()
    assert sub_dir.name == '_feature_'
    depth = len(sub_dir.parts)
    assert sub_dir.parent.name == '_testapp_'

    config_dir = await get_xdg_config_dir('_testapp_')
    assert await config_dir.exists()
    assert config_dir.name == '_testapp_'
    assert len(config_dir.parts) == depth - 1


async def test_get_xdg_config_dir_flipped(env_home):
    """Create a configuration directory for an app with the parent first."""
    set_env(env_home)

    config_dir = await get_xdg_config_dir('_testapp_')
    assert await config_dir.exists()
    assert config_dir.name == '_testapp_'
    depth = len(config_dir.parts)

    sub_dir = await get_xdg_config_dir('_testapp_', '_feature_')
    assert await sub_dir.exists()
    assert sub_dir.name == '_feature_'
    assert len(sub_dir.parts) == depth + 1
    assert sub_dir.parent.name == '_testapp_'


async def test_get_config(env_home, config_icecast):
    """Create a default config file for a command."""
    set_env(env_home)
    config_dir = await get_xdg_config_dir()
    config_file = config_dir / 'icecast.xml'
    assert not await config_file.exists()
    config = await get_config(config_dir, 'icecast.xml', **config_icecast)
    assert await config.exists()
    config_text = await config.read_text()
    for _, value in config_icecast.items():
        assert value in config_text


async def test_get_xdg_cache_dir(env_home):
    """Create a cache directory for an app."""
    set_env(env_home)

    # Check that a directory was created.
    cache_dir = await get_xdg_cache_dir('_testapp_')
    assert await cache_dir.exists()
    assert cache_dir.name == '_testapp_'

    # Make sure get_xdg_cache_dir returns a resolved path.
    xdg_cache_home = await Path(env_home['XDG_CACHE_HOME']).resolve()
    assert cache_dir.parent == xdg_cache_home


async def test_get_xdg_data_dir(env_home):
    """Create a data directory for an app."""
    set_env(env_home)

    # Check that a directory was created.
    data_dir = await get_xdg_data_dir('_testapp_')
    assert await data_dir.exists()
    assert data_dir.name == '_testapp_'

    # Make sure get_xdg_data_dir returns a resolved path.
    xdg_data_home = await Path(env_home['XDG_DATA_HOME']).resolve()
    assert data_dir.parent == xdg_data_home


async def test_get_xdg_runtime_dir(env_home):
    """Create a runtime directory for an app."""
    set_env(env_home)

    # Check that a directory was created.
    runtime_dir = await get_xdg_runtime_dir('_testapp_')
    assert await runtime_dir.exists()
    assert runtime_dir.name == '_testapp_'

    # Make sure get_xdg_runtime_dir returns a resolved path.
    xdg_runtime_home = await Path(env_home['XDG_RUNTIME_DIR']).resolve()
    assert runtime_dir.parent == xdg_runtime_home
