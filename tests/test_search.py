"""Search for music."""
import trio

from reel import cmd
from reel import config
from reel.proc import Source
from reel.tools import resolve

from tapedeck.search import find_tunes, is_audio
from tests.fixtures import music_dir


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


async def test_search(music_dir):
    """Find some music."""
    search = Source(f'python -m tapedeck.cli.main search {str(music_dir)}')
    # ... import coverage in default pyenv needed
    results = await search.read_list(through=resolve)
    assert search.status == 0
    assert len(results) == 3
    found = False
    for path in results:
        if path.endswith('subsubsubdir'):
            found = True
    assert found
    # ... hide dot files
    # ... hide symlinks


async def test_search_results(music_dir):
    """Find and list music folders."""
    search = Source(f'python -m tapedeck.cli.main search {str(music_dir)}')
    results = await search.read_list()

    # List search results.
    assert len(results) == 3

    # Show indexes numbering each result.
    idx = 0
    for line in results:
        idx += 1
        print(line)
        # ... hack to pass test - cmd.tapedeck.search strips whitespace ...
        assert (line[0] == str(idx)) or (line[2] == str(idx))

    # List the name of each folder (not the absolute path).
    filenames = []
    for line in results:
        filename = line[line.find(' ') + 1:]  # index number at start of line
        filenames.append(filename)
        assert not trio.Path(filename).is_absolute()

    # Do not repeat results.
    assert sorted(filenames) == sorted(list(set(filenames)))

    # Save a cache file with the search results.
    cache_dir = await config.get_xdg_cache_dir('tapedeck')
    assert await cache_dir.exists()
    cached_search = cache_dir / 'search.txt'
    assert await cached_search.exists()

    # Check for no dupes, but absolute paths, in cache file.
    async with await cached_search.open('r') as results:
        lines = (await results.read()).split('\n')[0:-1]
    filenames = []
    for line in lines:
        filename = line[line.find(' ') + 1:]  # index number at start of line
        filenames.append(filename)
        assert trio.Path(filename).is_absolute()
    assert sorted(filenames) == sorted(list(set(filenames)))
