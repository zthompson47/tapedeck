"""Use the sox play utility."""
import reel


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
    return reel.Spool(cmd, xflags=flags)
