"""Load the configuration environment."""
import logging
import os

from reel import get_xdg_config_dir


async def get_logger(logger_name):
    """Set the root tapedeck logger from the env config."""
    logger = logging.getLogger(logger_name)
    logging_level = await env('LOGGING_LEVEL')
    if logging_level:
        logging_file = await logfile('tapedeck.log')
        logger.addHandler(logging.FileHandler(logging_file))
    else:
        logging_level = 'WARN'
    logger.setLevel(logging_level)
    return logger


async def env(key=None):
    """Return the configuration based on current environment."""
    _log_dir = await get_xdg_config_dir('tapedeck')  # .. should be data_home
    _log_level = os.environ.get('TAPEDECK_LOGGING_LEVEL')
    if _log_level:
        _log_level = _log_level.upper()
    _env = {
        'LOGGING_LEVEL': _log_level,
        'LOGGING_DIR': os.environ.get('TAPEDECK_LOGGING_DIR', _log_dir),
        'UDP_HOST': os.environ.get('TAPEDECK_UDP_HOST'),
        'UDP_PORT': os.environ.get('TAPEDECK_UDP_PORT'),
    }
    if key:
        return _env[key]
    return _env


async def logfile(name):
    """Return a Path to a log file."""
    return await env('LOGGING_DIR') / name
