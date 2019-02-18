"""Various ffmpeg command line tools."""
from .._spool import Spool


def read(uri):
    """Prepare a command to read an audio file and stream to stdout."""
    cmd = 'ffmpeg'
    flags = [
        '-ac', '2',  # 2-channel stereo
        '-i', uri,  # input file or url
        '-f', 's16le',  # 16 bit little-endian
        '-ar', '44.1k',  # sample rate
        '-acodec', 'pcm_s16le',  # wav format
        '-',  # stream to stdout
    ]
    return Spool(cmd, xflags=flags)


def to_icecast(host, port, mount, password):
    """Stream audio to an icecast server."""
    cmd = 'ffmpeg'
    flags = [
        '-re',
        '-ac', '2',
        '-ar', '44.1k',
        '-f', 's16le',
        '-i', '-',
        '-vn',
        '-codec:a', 'libvorbis',
        '-q:a', '8.0',
        '-content_type', 'audio/ogg',
        '-f', 'ogg',
        f'icecast://source:{password}@{host}:{port}/{mount}'
    ]
    return Spool(cmd, xflags=flags)


def to_udp(host, port):
    """Stream audio over udp."""
    cmd = 'ffmpeg'
    flags = [
        '-re',  # realtime flow control
        '-ac', '2',  # 2-channel stereo
        '-ar', '44.1k',  # sample rate
        '-f', 's16le',  # 16 bit littl-endian
        '-i', '-',  # receive from stdin
        '-vn',  # no video
        '-acodec', 'mp3',  # compress to mp3
        '-q:a', '0',  # maximum quality
        '-f', 'mp3',  # mp3 format
        f'udp://{host}:{port}',  # receiver address
    ]
    return Spool(cmd, xflags=flags)


def to_file(path):
    """Stream to a file."""
    cmd = 'ffmpeg'
    flags = [
        '-ac', '2',  # 2-channel stereo
        '-ar', '44.1k',  # sample rate
        '-f', 's16le',  # 16 bit little-endian
        '-i', '-',  # receive from stdin
        '-f', 's16le',  # 16 bit little-endian
        '-ar', '44.1k',  # sample rate
        '-y',  # overwrite output file
        '-c:a', 'copy',  # stream copy audio
        path,
    ]
    return Spool(cmd, xflags=flags)
