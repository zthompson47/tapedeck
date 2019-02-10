"""Test suite for the :mod:`reel.cli` command line interface."""
import reel


async def test_no_args(cli_cmd):
    """Run :mod:`reel.cli` with no arguments."""
    noargs = reel.Spool(cli_cmd)
    output = await noargs.run()
    assert noargs.returncode == 0
    assert output == 'leer'


async def test_version(cli_cmd):
    """Show the version number."""
    for flag in ['-v', '--version']:
        command = f'{cli_cmd} {flag}'
        version = reel.Spool(command)
        output = await version.run()
        assert version.returncode == 0
        assert output == reel.__version__


async def test_config(cli_cmd):
    """Show the current configuration."""
    for flag in ['-c', '--config']:
        command = f'{cli_cmd} {flag}'
        config = reel.Spool(command, {'REEL_LOG_LEVEL': 'debug'})
        dump = (await config.run()).split('\n')
        assert len(dump) == 3
        assert config.returncode == 0
        for line in dump:
            assert line.startswith('REEL_')
