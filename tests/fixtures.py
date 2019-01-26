"""Shared test fixtures and functions."""
import logging
import os

import pytest

import tapedeck

ENV_COVERAGE = {
    'COVERAGE_PROCESS_START': 'setup.cfg',
    'PYTHONPATH': '.'
}
RADIO = 'http://ice1.somafm.com/groovesalad-256-mp3'

logging.basicConfig(
    filename=tapedeck.LOGGING_FILE,
    level=tapedeck.LOGGING_LEVEL
)


@pytest.fixture
def env_audio_dest():
    """Enable setting an audio output for testing."""
    return os.environ.get('TAPEDECK_TESTING_AUDIO_DEST', '/dev/null')


@pytest.fixture
def music_dir(tmpdir):
    """Create a temporary directory with of music subdirectories."""
    music_dirs = [
        {
            'root1': [
                {'Some folder.shnf': ['asdf.wav']},
                {'some other folder': ['rr.txt', 'asdf.wav', 'eHello~!.doc']},
                {'subdir': [
                    {'subsubdir': [
                        {'subsubsubdir': ['asdfasdfasdfasdf.aac']},
                    ]},
                    [],
                ]},
                [],
                'rootfile.txt',
                {'yeah whatev': []},
            ],
        },
    ]

    def create_nodes(structure, parent_node=None):
        """Create a filesystem from a template `structure`."""
        result = None
        for node in structure:
            if isinstance(node, dict):
                for subnode in node.keys():
                    if parent_node:
                        result = parent_node.join(subnode).mkdir()
                    else:
                        result = tmpdir.join(subnode).mkdir()
                    create_nodes(node[subnode], result)
            elif isinstance(node, list):
                for subnode in node:
                    create_nodes(subnode, parent_node)
            elif isinstance(node, str):
                if parent_node:
                    parent_node.join(node).write('yup')
        return result
    return str(create_nodes(music_dirs))
