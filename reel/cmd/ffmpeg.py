"""Various ffmpeg command line configurations."""
from reel.proc import Destination, Source


async def stream(uri):
    """Stream an audio source."""
    cmd = 'ffmpeg'
    flags = ['-ac', '2',
             '-i', uri,
             '-f', 's16le',
             '-ar', '44.1k',
             '-acodec', 'pcm_s16le',
             '-']
    return await Source(cmd, xconf=flags).stream()


async def udp(ipaddr='192.168.1.100', port='6667'):
    """Stream audio over udp."""
    cmd = 'ffmpeg'
    flags = ['-re',
             '-ac', '2',
             '-ar', '44.1k',
             '-f', 's16le',
             '-i', '-',
             '-vn',
             '-acodec', 'mp3',
             '-q:a', '0',
             '-f', 'mp3',
             f'udp://{ipaddr}:{port}']
    return await Destination(cmd, xconf=flags).receive()
