"""Use the sox play utility."""
import reel
from reel.proc import Destination


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
    return reel.Spool(cmd, xconf=flags)


def play():
    """Send audio to the speaker."""
    cmd = 'play'
    flags = ['-t', 'raw',
             '-r', '44.1k',
             '-e', 'signed-integer',
             '-b', '16',
             '--endian', 'little',
             '-c', '2',
             '-']
    return Destination(cmd, xconf=flags).receive()
