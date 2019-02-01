"""Test loading the tapedeck module."""
from reel import Path

import tapedeck


def test_tapedeck_package():
    """Import tapedeck from the project directory of this test."""
    assert tapedeck
    project_dir = Path(__file__).parent.parent
    assert tapedeck.__file__ == str(project_dir / 'tapedeck' / '__init__.py')
