"""Install the tapedeck package."""
from setuptools import find_packages, setup

setup(
    license='MIT',
    name='tapedeck',
    version=open('VERSION', 'r').read().strip(),
    author='Zach Thompson',
    author_email='zach@allotropic.com',
    url='http://github.com/zthompson47/tapedeck',
    description='A music player',
    long_description_content_type='text/x-rst',
    long_description=open('README.rst', 'r').read(),
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'tapedeck=tapedeck.cli.main:tapedeck_cli',
            'tdplay=tapedeck.cli.play:enter',
            'tdsearch=tapedeck.cli.search:enter',
        ],
    },
    install_requires=[
        'blessings>=1.7',
        'reel>=0.0.5',
        'trio>=0.10.0',
    ],
    zip_safe=False,
    packages=find_packages(),
)
