"""Pre-configured commands."""
from . import ffmpeg, icecast, sox

SRC_SILENCE = "ffmpeg -re -f s16le -i /dev/zero -f s16le -"

SRC_FILE = "ffmpeg -ac 2 -i {filename} -f s16le -ar 44.1k -acodec pcm_s16le -"


PYP_NORMED = """fmpeg -ac 2 -i {filename} -af loudnorm=I=-16:TP=-1.5:LRA=11
                -ac 2 -f s16le -ar 44.1k -acodec pcm_s16le -"""


DST_UDP = """ffmpeg -re -ac 2 -ar 44.1k -f s16le -i -
             -vn -acodec mp3 -q:a 0 -f mp3 udp://{ipaddress}:{port}"""

DST_ICECAST = """ffmpeg -re -ac 2 -ar 44.1k -f s16le -i -
                 -vn -acodec mp3 -q:a 0 -f mp3
                 icecast://source:{password}@{host}:{port}/{mount}"""

DST_SPEAKER = """play -t raw -r 44.1k -e signed-integer
                 -b 16 --endian little -c 2 -"""
