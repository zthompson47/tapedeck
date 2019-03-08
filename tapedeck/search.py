"""Search for music."""
import logging
import os
from typing import List

from trio import Path

from reel.config import get_xdg_cache_dir

LOG = logging.getLogger(__name__)


class Folder:
    """A folder of music."""

    def __init__(self, **kwargs):
        """Create a folder."""
        self._path = ''
        self.song_files = []
        self.text_files = []
        for key, value in kwargs.items():
            if key == 'path':
                self._path = value
            else:
                self.__setattr__(key, value)
        LOG.debug('__init__:%s', self)

    def __repr__(self):
        """Print prettily."""
        return f"Folder('{self._path}')"

    @property
    def path(self):
        """Return this path."""
        return self._path


async def cached_search(index: int) -> Path:
    """Return the path to a cached search entry."""
    cache_file = await get_xdg_cache_dir('tapedeck') / 'search.txt'
    async with await cache_file.open('r') as cache:
        lines = (await cache.read()).split('\n')[0:-1]
    track = lines[index - 1]
    return Path(track[track.find(' ') + 1:])


async def scan_folder(folder):
    """Return a list of songs found in a folder."""
    songs = [_ for _ in await folder.iterdir() if await _.is_file()]
    songs.sort()
    result = []
    for song in songs:
        if is_audio(str(song)):
            result.append(song)
    return result


async def find_tunes(music_dir: str,
                     followlinks=False,
                     followdots=False) -> List[Folder]:
    """Scan a list of directories for music files."""
    results = []
    logging.info("Scanning for music files...")
    for dirname, dirs, files in os.walk(music_dir, followlinks=followlinks):

        # Skip dotfile directories beginning with '.'.
        # https://stackoverflow.com/questions/13454164\
        #       /os-walk-without-hidden-folders
        if not followdots:
            dirs[:] = [_ for _ in dirs if not _[0] == '.']

        song_files = []
        text_files = []
        for fname in files:
            if is_audio(fname):
                song_files.append(fname)
            if fname.endswith('.txt'):
                text_files.append(fname)
        if song_files:
            folder = Folder(
                path=os.path.abspath(dirname),
                song_files=song_files,
                text_files=text_files,
            )
            results.append(folder)
    return results


def is_audio(filename: str) -> bool:
    """Check for audio file extensions."""
    for ext in ['.flac', '.mp3', '.wav', '.shn', '.aac', '.m4a', '.aiff']:
        if filename.lower().endswith(ext):
            return True
    return False
