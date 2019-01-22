"""Use the sox play utility."""
from reel.proc import Destination


async def speaker():
    """Send audio to the speaker."""
    flags = ['-t', 'raw',
             '-r', '44.1k',
             '-e', 'signed-integer',
             '-b', '16',
             '--endian', 'little',
             '-c', '2',
             '-']
    return await Destination('play', xconf=flags).receive()
