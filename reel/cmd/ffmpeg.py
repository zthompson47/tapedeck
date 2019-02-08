"""Various ffmpeg command line tools."""
import reel


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
    return reel.Spool(cmd, xflags=flags)


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
    return reel.Spool(cmd, xflags=flags)


def to_file2(path):
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
    return reel.Spool(cmd, xflags=flags)
