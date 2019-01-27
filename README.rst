Tapedeck
========

Tapedeck finds and plays music across muiltiple sources and devices::

   $ pip install tapedeck
   $ tapedeck play --recursive --shuffle ~/Music -o speakers

**And the band keeps playing on...**
   -- John Perry Barlow

Usage
-----

Play a music folder::

   $ tapedeck play shows/gd1980-07-01.139309.sbd.moore.berger.flac24/
   gd1980-07-01.139309.sbd.moore.berger.flac24 / gd80-07-01s1t01.flac
   gd1980-07-01.139309.sbd.moore.berger.flac24 / gd80-07-01s1t02.flac

Find music and play a folder::

   $ tapedeck search ~/Downloads
    ...
     4. ny1969-xx-xx/
     5. ny1970-xx-xx/
     6. oaitw1973-xx-xx/
    ...
   $ tapedeck play -c 5

View the last search::

   $ tapedeck search -c
    ...
     4. ny1969-xx-xx/
     5. ny1970-xx-xx/
     6. oaitw1973-xx-xx/
    ...
   $

Stream music to a device::

   $ tapedeck play . -o udp -h 192.168.1.100 -p 8771

Installation
------------

Follow the three-step installation process for your system:

Mac
~~~

1. Install `Homebrew <http://brew.sh>`_ -
   "The missing package manager for macOS".

2. Install some handy programs that ``tapedeck`` requires::

   $ brew install python3 ffmpeg sox aria2 postgresql icecast2

3. Install ``tapedeck``::

   $ pip3 install tapedeck

Android
~~~~~~~

1. Install termux
2. Install deps
3. ``pip install tapedeck``

Windows
~~~~~~~

1. ``git clone http://github.com/zthompson47/tapedeck``
2. make it happen
3. let me know

iPhone
~~~~~~

1. refer
2. to
3. above

Motivation
----------

After decades of various physical media and enough spooled tape
to lasso the moon, we find ourselves at the internet.  Many large
collections of live music are available online for free: LEGALLY
traded by a resilient community of music fanatics.  Meanwhile, many
of us now own multiple networked devices that are capable of music
download, streaming, and playback.  We also own piles of media purchases
that (hopefully) still exist in physical format to be ripped.

Tapedeck strives to organize these collections of music and provide
a way for the you to enjoy your stash.

