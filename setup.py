"""Install the tapedeck package."""
from setuptools import find_packages, setup

setup(
    license="MIT",
    name="tapedeck",
    version=open("VERSION", "r").read().strip(),
    author="Zach Thompson",
    author_email="zach@allotropic.com",
    url="http://github.com/zthompson47/tapedeck",
    description="A metashell for mpd + aria2 + rss",
    long_description_content_type="text/x-rst",
    long_description=open("README.rst", "r").read(),
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        "console_scripts": [
            "tapedeck=tapedeck.__main__:enter",
    #        'tdplay=tapedeck.cli.play:enter',
    #        'tdsearch=tapedeck.cli.search:enter',
        ],
    },
    install_requires=[
        "trio",
        "trio-websocket",
        "prompt-toolkit",
        "feedparser",
        "redis",
        "pyudev",
        "jeepney",
    ],
    zip_safe=False,
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
