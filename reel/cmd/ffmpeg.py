"""Various ffmpeg command line tools."""
from reel.proc import Destination, Source


async def stream(uri):
    """Stream an audio source."""
    cmd = 'ffmpeg'
    flags = ['-ac', '2',  # 2-channel stereo
             '-i', uri,  # input file or url
             '-f', 's16le',  # 16 bit little-endian
             '-ar', '44.1k',  # sample rate
             '-acodec', 'pcm_s16le',  # wav format
             '-']  # stream to stdout
    return await Source(cmd, xconf=flags).stream()


async def udp(ipaddr='192.168.1.100', port='6667'):
    """Stream audio over udp."""
    cmd = 'ffmpeg'
    flags = ['-re',  # realtime flow control
             '-ac', '2',  # 2-channel stereo
             '-ar', '44.1k',  # sample rate
             '-f', 's16le',  # 16 bit littl-endian
             '-i', '-',  # receive from stdin
             '-vn',  # no video
             '-acodec', 'mp3',  # compress to mp3
             '-q:a', '0',  # maximum quality
             '-f', 'mp3',  # mp3 format
             f'udp://{ipaddr}:{port}']  # receiver address
    return await Destination(cmd, xconf=flags).receive()
