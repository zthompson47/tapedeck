"""The runtime configuration environment.

The config module reads settings from environment variables and
assigns defaults when appropriate.

"""
import os

from ._path import Path

__all__ = [
    'get_config',
    'get_package_dir', 'get_package_name',
    'get_xdg_home', 'get_xdg_config_dir',
    'get_config', 'get_xdg_cache_dir',
    'get_xdg_data_dir', 'get_xdg_runtime_dir',
]


async def get_package_dir():
    """Return the file path to this package's directory."""
    return (await Path(__file__).resolve()).parent


async def get_package_name():
    """Return the name of this package."""
    return (await get_package_dir()).name


async def get_xdg_home(choice=None):
    """Return the root configuration directories for this environment."""
    home_env = {
        'XDG_CONFIG_HOME': await Path.canon('~/.config'),
        'XDG_CACHE_HOME': await Path.canon('~/.cache'),
        'XDG_DATA_HOME': await Path.canon('~/.local/share'),
        'XDG_RUNTIME_DIR': await Path.canon('~/.local/run'),
    }

    # Override the defaults if already set in an environment variable.
    for key in home_env:
        home_env[key] = os.environ.get(key, home_env[key])

    if choice:
        return home_env[choice]
    return home_env


async def get_xdg_config_dir(app=None, feature=None):
    """Return a config directory for this app.

    Create the directory if it does not exist.

    """
    if app is None:
        app = await get_package_name()
    config_home = Path(await get_xdg_home('XDG_CONFIG_HOME'))
    config_dir = config_home / app
    if not await config_dir.exists():
        await config_dir.mkdir()
    if feature:
        config_dir = config_dir / feature
    if not await config_dir.exists():
        await config_dir.mkdir()
    return config_dir


async def get_config(config_path, template_file, **xconf):
    """Create a config file from a template."""
    config_file = config_path / template_file
    if not await config_file.exists():
        default_file = (await get_package_dir()) / 'templates' / template_file
        formatted = (await default_file.read_text()).format(**xconf)
        await config_file.write_text(formatted)
    return config_file


async def get_xdg_cache_dir(app=None):
    """Return a cache directory for this app.

    Create the directory if it does not exist.

    """
    if app is None:
        app = await get_package_name()
    cache_home = Path(await get_xdg_home('XDG_CACHE_HOME'))
    cache_dir = cache_home / app
    if not await cache_dir.exists():
        await cache_dir.mkdir()
    return await cache_dir.resolve()


async def get_xdg_data_dir(app=None):
    """Return a data directory for this app.

    Create the directory if it does not exist.

    """
    if app is None:
        app = await get_package_name()
    data_home = Path(await get_xdg_home('XDG_DATA_HOME'))
    data_dir = data_home / app
    if not await data_dir.exists():
        await data_dir.mkdir()
    return await data_dir.resolve()


async def get_xdg_runtime_dir(app=None):
    """Return a runtime directory for this app.

    Create the directory if it does not exist.

    """
    if app is None:
        app = await get_package_name()
    runtime_home = Path(await get_xdg_home('XDG_RUNTIME_DIR'))
    runtime_dir = runtime_home / app
    if not await runtime_dir.exists():
        await runtime_dir.mkdir()
    return await runtime_dir.resolve()
