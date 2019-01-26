"""Use the sox play utility."""
from reel.proc import Destination


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
