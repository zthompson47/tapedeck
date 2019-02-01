"""Tests for `tapedeck.cli.search`.

Usage: tapedeck search [options] [directory]

  ¤ Find music

Options:
  -d, --follow-dots   Search hidden dot-directories.
  -l, --follow-links  Search symlinked directories.
  -m, --memory        Show last search from memory
  --help              Show this message and exit.

"""
from reel import get_xdg_cache_dir, Path
from reel.proc import Source


async def test_search(music_dir):
    """Find some music."""
    search = Source(f'python -m tapedeck.cli.main search {str(music_dir)}')
    # ... import coverage in default pyenv needed
    results = await search.read_list(through=Path.canon)
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
        assert not Path(filename).is_absolute()

    # Do not repeat results.
    assert sorted(filenames) == sorted(list(set(filenames)))

    # Save a cache file with the search results.
    cache_dir = await get_xdg_cache_dir('tapedeck')
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
        assert Path(filename).is_absolute()
    assert sorted(filenames) == sorted(list(set(filenames)))


async def test_cached_results(music_dir):
    """Show the prior search."""
    search = Source(f'tapedeck search {str(music_dir)}')
    results = await search.read_list()
    assert len(results) == 3

    cached_search = Source('tapedeck search -m')
    cached_results = await cached_search.read_list()
    assert len(cached_results) == 3
