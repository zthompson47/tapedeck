"""Inject full coverage for subprocess tests.

A subprocess is not run under the 'coverage' command, so we need to inject
a hook in the local python site to enable coverage.  If this directory is
in sys.path, this file will be imported, and the coverage code will run.
Since there might have already been a site-wide sitecustomize.py file,
we search for that file and force an import with importlib.reload.

"""
from importlib import reload
import os
from pathlib import Path
import sys

# Only import this file if explicitly wanted.
if os.environ.get('REEL_SITECUSTOMIZE'):

    if Path('.').resolve() == Path(__file__).resolve().parent:
        import coverage
        coverage.process_startup()

    # Temporarily alter sys.path so we can reload this module and pick
    # up the default sitecustomize.py file, if it exists.
    _SYS_PATH = list(sys.path)
    _CWD = str(Path('.').resolve())
    while _CWD in sys.path:
        sys.path.remove(_CWD)
    try:
        import sitecustomize  # pylint: disable=import-self
        reload(sitecustomize)
    except ImportError:
        pass
    sys.path = _SYS_PATH
