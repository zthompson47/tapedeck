"""Install the tapedeck package."""
from setuptools import setup

setup(
    license='MIT',
    name='tapedeck',
    packages=['tapedeck'],
    version='0.0.1',
    author='Zach Thompson',
    author_email='zach@allotropic.com',
    url='http://github.com/zthompson47/tapedeck',
    description='A music player',
    long_description=open('README.rst', 'r').read(),
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['tapedeck=tapedeck.cli:main'],
    },
    install_requires=[
        'trio>=0.10.0',
        'trio-click>=7.0.2',
        'reel',
    ],
    zip_safe=False,
)
