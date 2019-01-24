"""Tapedeck command line tools."""
from reel.proc import Source


async def search(search_dir):
    """Search for music recursively in a directory."""
    cmd = 'tapedeck'
    flags = ['search', str(search_dir)]
    return await Source(cmd, xconf=flags).read_list()
