"""Various ffmpeg command line configurations."""
from reel.proc import Source


async def stream(uri):
    """Stream an audio source."""
    flags = ['-ac', '2',
             '-i', uri,
             '-f', 's16le',
             '-ar', '44.1k',
             '-acodec', 'pcm_s16le',
             '-']
    return await Source('ffmpeg', xconf=flags).stream()
