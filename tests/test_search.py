"""Tests for the tapedeck.search module."""
from tapedeck.search import find_tunes, is_audio


async def test_find_tunes(music_dir):
    """Search fixture directories for music-like file extensions."""
    folders = await find_tunes(music_dir)
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
