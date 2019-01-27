"""Search for music."""
import logging
import os
from typing import List

import trio

from reel.tools import resolve


class Folder:
    """A folder of music."""

    def __init__(self, **kwargs):
        """Create a folder."""
        self.path = ''
        self.song_files = []
        self.text_files = []
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    def _pretty_print(self):
        """Print prettily."""
        result = 'Folder:/'
        parent = trio.run(trio.Path(self.path).parent.resolve)
        for part in parent.parts:
            if part[0] != '/':
                result += part[0] + '/'
        result += trio.Path(self.path).name
        return result

    def __repr__(self):
        """Print prettily."""
        return self._pretty_print()

    def __str__(self):
        """Print prettily."""
        return self._pretty_print()


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
                path=await resolve(dirname),  # ... test absolute path ...
                song_files=song_files,
                text_files=text_files,
            )
            results.append(folder)
    return results


def is_audio(filename: str) -> bool:
    """Check for audio file extensions."""
    for ext in ['.flac', '.mp3', '.wav', '.shn', '.aac', '.m4a']:
        if filename.lower().endswith(ext):
            return True
    return False
