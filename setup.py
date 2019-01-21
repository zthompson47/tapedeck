"""Install the tapedeck package."""
from setuptools import setup

setup(
    name='tapedeck',
    description='''Tapedeck finds and plays music
                   across muiltiple sources and devices.''',
    url='http://github.com/zthompson47/tapedeck',
    author='Zach Thompson',
    author_email='zach@allotropic.com',
    license='MIT',
    packages=['tapedeck'],
    zip_safe=False,
    entry_points={
        'console_scripts': ['tapedeck=tapedeck.cli:main'],
    },
    install_requires=[
        'trio>=0.10.0',
        'trio-click>=7.0.2',
        'reel',
    ],
)
