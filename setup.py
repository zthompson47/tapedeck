"""Install the reel package."""
from setuptools import setup


setup(
    name='reel',
    version='0.0.1',
    author='Zach Thompson',
    author_email='zach@allotropic.com',
    description='A package for async subprocesses',
    long_description=open('README.rst', 'r').read(),
    url='http://github.com/zthompson47/reel',
    packages=['reel'],
    license='MIT',
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['reel=reel.cli:main'],
    },
    install_requires=[
        'trio>=0.10.0',
        'trio-click>=7.0.2',
    ],
)
