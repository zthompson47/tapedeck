"""Use the sox play utility."""
from .._spool import Spool


def speakers():
    """Send audio to the speaker."""
    cmd = 'play'
    flags = ['-t', 'raw',
             '-r', '44.1k',
             '-e', 'signed-integer',
             '-b', '16',
             '--endian', 'little',
             '-c', '2',
             '-']
    return Spool(cmd, xflags=flags)
