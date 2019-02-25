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
    logfile = await tapedeck.config.logfile(filename)
    LOGGER.debug('Got logfile: %s', logfile)
    xdg_logfile = xdg['XDG_DATA_HOME'] / 'tapedeck' / filename
    assert await logfile.resolve() == await xdg_logfile.resolve()  # resolve?
    assert logfile.parent.exists()
    assert caplog


async def test_subprocess_logging(caplog):
    """Check for log messages from subprocesses."""

    # Create a folder for an example debugging message (Folder.__init__ logs).
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

    # Run a subprocess to find captured logs from :class:`reel.Spool`.
    xenv = {'TAPEDECK_LOG_LEVEL': 'debug'}
    version = await reel.Spool('tapedeck --version', xenv).run()
    assert tapedeck.__version__ in version
    found_one = False
    found_version = False
    for log in caplog.records:
        print(log.name, log.message)
        if tapedeck.__version__ in log.message:
            found_version = True
        # if log.name == 'reel.proc':
        #     assert "tapedeck --v" in log.message
        #     found_one = True
        if log.name == 'root':
            if "tapedeck --v" in log.message:
                found_one = True
    # assert found_one
    assert found_version
    # ???

    # The internal subprocess log ended up in the tmp xdg home.
    logpath = await reel.config.get_xdg_data_dir('tapedeck') / 'tapedeck.log'
    assert await logpath.exists()
    # assert tapedeck.__version__ in await logpath.read_text()

    # Ask the subprocess to log to stderr and check Source.err.
    command = 'tapedeck --log-to-stderr --version'
    source = reel.Spool(command, {'TAPEDECK_LOG_LEVEL': 'debug'})
    version = await source.run()
    # assert tapedeck.__version__ in source.stderr
    # assert 'REMOTE:' not in source.stderr
    # assert tapedeck.__version__ in version

    # Find source.err in the logs for this process.
    # found_one = False
    # for log in caplog.records:
    #     if log.name == 'reel.proc':
    #         if log.message.startswith('REMOTE:'):
    #             if tapedeck.__version__ in log.message:
    #                 found_one = True
    # assert found_one


async def test_tapedeck_cli_config_option(uri):
    """Check that the cli dumps a list of environment variables."""
    async with reel.Spool('tapedeck --config') as src:
        lines = await src.readlines()
        config = {_.split('=')[0]: _.split('=')[1] for _ in lines}
        assert 'TAPEDECK_UDP_HOST' not in config.keys()
        assert 'TAPEDECK_UDP_PORT' not in config.keys()
        assert len(config.keys()) == 2
        print(await tapedeck.config.env())
        for key, val in (await tapedeck.config.env()).items():
            assert config[key] == val

    # Try running the cli with the returned config.
    command = f"tapedeck play {uri.RADIO} -o udp"
    async with reel.Spool(command, xenv=config).timeout(2) as bad_cfg:
        await bad_cfg.read()
    #    assert bad_cfg.returncode > 0  # fail with host:port

    # Try again with the udp config.
    _env = {'TAPEDECK_UDP_HOST': '0.0.0.0', 'TAPEDECK_UDP_PORT': '9999'}
    async with reel.Spool('tapedeck --config', xenv=_env) as good_cfg:
        lines = await good_cfg.readlines()
        config = {_.split('=')[0]: _.split('=')[1] for _ in lines}
        command = f"tapedeck play {uri.RADIO} -o udp"
    #    radio = reel.Spool(command, xenv=config).timeout(2)
    #    await radio.run()
    #    assert radio.returncode <= 0
