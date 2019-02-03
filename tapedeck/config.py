"""Load the configuration environment."""
import logging
import os

import reel


async def get_logger(logger_name):
    """Set the root tapedeck logger from the env config."""
    logger = logging.getLogger(logger_name)
    logging_level = await env('TAPEDECK_LOG_LEVEL')
    if logging_level:
        logging_file = await logfile('tapedeck.log')
        logger.addHandler(logging.FileHandler(logging_file))
    else:
        logging_level = 'WARN'
    logger.setLevel(logging_level)
    return logger


async def env(var=None):
    """Return the configuration based on current environment."""
    log_dir = await reel.get_xdg_config_dir('tapedeck')  # ... data_home
    log_level = os.environ.get('TAPEDECK_LOG_LEVEL', 'warn').upper()

    _env = {
        'TAPEDECK_LOG_LEVEL': log_level,
        'TAPEDECK_LOG_DIR': os.environ.get('TAPEDECK_LOG_DIR', str(log_dir)),
        'TAPEDECK_UDP_HOST': os.environ.get('TAPEDECK_UDP_HOST'),
        'TAPEDECK_UDP_PORT': os.environ.get('TAPEDECK_UDP_PORT'),
    }

    if var:
        return _env[var]
    return {key: val for key, val in _env.items() if val is not None}


async def logfile(name):
    """Return a Path to a log file."""
    return reel.Path(await env('TAPEDECK_LOG_DIR')) / name
