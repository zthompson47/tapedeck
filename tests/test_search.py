"""Search for music."""
from tapedeck.search import find_tunes, is_audio
from tests.fixtures import music_dir  # pylint: disable=W0611


def test_find_tunes(music_dir):  # pylint: disable=W0621
    """Search fixture directories for music-like file extensions."""
    folders = find_tunes(music_dir)
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
