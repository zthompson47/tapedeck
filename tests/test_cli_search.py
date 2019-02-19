"""Tests for `tapedeck.cli.search`.

Usage: tapedeck search [options] [directory]

  ¤ Find music

Options:
  -d, --follow-dots   Search hidden dot-directories.
  -l, --follow-links  Search symlinked directories.
  -m, --memory        Show last search from memory
  --help              Show this message and exit.

"""
import reel
from reel.config import get_xdg_cache_dir


async def test_search(music_dir):
    """Find some music."""
    cmd = reel.Spool(f'python -m tapedeck.cli.main search {str(music_dir)}')
    async with cmd as search:
        # ... import coverage in default pyenv needed
        lines = await search.readlines()
        results = [await reel.Path.canon(_) for _ in lines]
        assert len(results) == 3
        found = False
        for path in results:
            if path.endswith('subsubsubdir'):
                found = True
        assert found
        # assert search.returncode == 0
    # ... hide dot files
    # ... hide symlinks


async def test_search_results(music_dir):
    """Find and list music folders."""
    cmd = reel.Spool(f'python -m tapedeck.cli.main search {str(music_dir)}')
    async with cmd as search:
        results = await search.readlines()

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
            filename = line[line.find(' ') + 1:]  # remove index
            filenames.append(filename)
            assert not reel.Path(filename).is_absolute()

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
            filename = line[line.find(' ') + 1:]  # remove index
            filenames.append(filename)
            assert reel.Path(filename).is_absolute()
        assert sorted(filenames) == sorted(list(set(filenames)))


async def test_cached_results(music_dir):
    """Show the prior search."""
    cmd = reel.Spool(f'tapedeck search {str(music_dir)}')
    async with cmd as search:
        results = await search.readlines()
        assert len(results) == 3

        cmd2 = reel.Spool('tapedeck search -m')
        async with cmd2 as cached_search:
            cached_results = await cached_search.readlines()
            assert len(cached_results) == 3


async def test_cached_results_with_tdsearch(music_dir):
    """Show the prior search."""
    cmd = reel.Spool(f'tdsearch {str(music_dir)}')
    async with cmd as search:
        results = await search.readlines()
        assert len(results) == 3

        cmd2 = reel.Spool('tdsearch -m')
        async with cmd2 as cached_search:
            cached_results = await cached_search.readlines()
            assert len(cached_results) == 3
