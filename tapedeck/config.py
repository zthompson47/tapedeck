"""Load the configuration environment."""
import os

import reel


async def env(var=None):
    """Return the configuration based on current environment."""
    log_dir = await reel.config.get_xdg_data_dir('tapedeck')
    log_level = os.environ.get('TAPEDECK_LOG_LEVEL')
    if log_level:
        log_level = log_level.upper()

    _env = {
        'TAPEDECK_LOG_LEVEL': log_level,
        'TAPEDECK_LOG_DIR': os.environ.get('TAPEDECK_LOG_DIR', str(log_dir)),
        'TAPEDECK_UDP_HOST': os.environ.get('TAPEDECK_UDP_HOST'),
        'TAPEDECK_UDP_PORT': os.environ.get('TAPEDECK_UDP_PORT'),
    }

    # Send one item if called with an argument.
    if var:
        return _env[var]

    # Return items that have a value.
    return {key: val for key, val in _env.items() if val is not None}


async def logfile(name):
    """Return a Path to a log file."""
    return reel.Path(await env('TAPEDECK_LOG_DIR')) / name
