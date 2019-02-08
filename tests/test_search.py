"""Tests for the tapedeck.search module."""
# import pytest

from reel import Path

from tapedeck.search import find_tunes, is_audio, Folder


async def test_find_tunes(music_dir):
    """Search fixture directories for music-like file extensions."""
    folders = await find_tunes(music_dir)
    assert isinstance(folders, list)
    assert len(folders) == 3


async def test_find_tunes_dots(music_dir):
    """Search fixture directories for music, following hidden directories."""
    folders = await find_tunes(music_dir, followdots=True)
    assert isinstance(folders, list)
    assert len(folders) == 3


def test_is_audio():
    """Make sure we can detect audio file types. """
    assert is_audio('asdf.mp3')
    assert is_audio(' asdf df dfas dfasdf lllllasdf.aac')
    assert is_audio('asdf.mp3')
    assert is_audio('asdf.mp3')
    assert is_audio(' asdf df dfas dfasdf lllllasdf.SHN')
    assert is_audio('asdf.mp3')
    assert not is_audio('asdf.txt')


def test_folder_print(tmpdir):
    """Print the folder prettily, keeping final name in path."""
    folder = Folder(path=tmpdir)
    assert folder
    assert Path(folder.path) in str(folder)
