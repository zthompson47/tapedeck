"""Use the sox play utility."""
from reel.proc import Destination


async def play():
    """Send audio to the speaker."""
    cmd = 'play'
    flags = ['-t', 'raw',
             '-r', '44.1k',
             '-e', 'signed-integer',
             '-b', '16',
             '--endian', 'little',
             '-c', '2',
             '-']
    return await Destination(cmd, xconf=flags).receive()
