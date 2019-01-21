"""Use the sox play utility."""
from reel.proc import Destination


def speaker():
    """Send audio to the speaker."""
    flags = ['-t', 'raw',
             '-r', '44.1k',
             '-e', 'signed-integer',
             '-b', '16',
             '--endian', 'little',
             '-c', '2',
             '-']
    return Destination('play', xconf=flags).receive()
