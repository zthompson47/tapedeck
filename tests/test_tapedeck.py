"""Test loading the tapedeck module."""
from pathlib import Path


def test_tapedeck():
    """Import tapedeck from the root project directory."""
    import tapedeck
    assert tapedeck
    project_dir = Path(__file__).parent.parent
    assert tapedeck.__file__ == str(project_dir / 'tapedeck' / '__init__.py')
