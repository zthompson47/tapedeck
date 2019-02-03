"""Tests for environment and configuration."""
import logging

import reel

import tapedeck
import tapedeck.search

LOGGER = logging.getLogger(__name__)


async def test_tapedeck_logfile(caplog, xdg):
    """Get a path to a usable log file based on app config."""
    LOGGER.debug('RUNNING TEST: test_tapedeck_logfile')
    filename = 'abracadabra.log'
    logfile = await tapedeck.logfile(filename)
    LOGGER.debug('Got logfile: %s', logfile)
    assert logfile == xdg['XDG_CONFIG_HOME'] / 'tapedeck' / filename
    assert logfile.parent.exists()
    assert caplog


async def test_subprocess_logging(caplog, xdg):
    """Check for log messages from subprocesses."""

    # Create a folder to log a debugging message (Folder.__init__ logs).
    path = '/some/path/to/a/folder'
    folder = tapedeck.search.Folder(path=path)
    assert folder.path == path  # do something with folder for pylint

    # Find the pytest captured debugging message.
    found_one = False
    for log in caplog.records:
        if log.name == 'tapedeck.search':
            assert 'h/to/a/f' in log.message
            found_one = True
    assert found_one

    # Run a subprocess to find captured logs from reel.Source.__init__.
    xenv = {'TAPEDECK_LOGGING_LEVEL': 'debug'}
    version = await reel.Source('tapedeck --version', xenv).read_text()
    assert tapedeck.__version__ in version
    found_one = False
    for log in caplog.records:
        if log.name == 'reel.proc':
            assert "Source() taped" in log.message
            found_one = True
    assert found_one

    # The internal subprocess log ended up in the tmp xdg home.
    logpath = await reel.get_xdg_config_dir('tapedeck') / 'tapedeck.log'
    print(logpath)
    assert await logpath.exists()
    assert tapedeck.__version__ in await logpath.read_text()

    # Ask the subprocess to log to stderr and check Source.err.
    command = 'tapedeck --log-to-stderr --version'
    source = reel.Source(command)
    version = await source.read_text()
    assert tapedeck.__version__ in source.err
    assert tapedeck.__version__ in version

    # print(dir(caplog.records[0]), caplog.records)
    # assert False
