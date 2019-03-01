Tapedeck
========

Tapedeck finds and plays music across muiltiple sources and devices::

   $ pip install tapedeck


One way to use it
-----------------

Perform a search::

   $ tdsearch Music
     1. Elegant Gypsy
     2. Exile On Main St. (Remastered)
     3. Highwayman
     4. Roll On (Bonus Track Version)
     5. Sleepless Nights
     6. The Essential Donovan
     7. Townes Van Zandt
     8. Skull Fu^H^H and Roses
   $ tdplay -m 7 -o icecast

Play the stream remotely::

   ~> tdplay http://192.168.1.100:8777/asdf  # ip address of your machine here

View the cached search::

   $ tdsearch -m
     1. Elegant Gypsy
     2. Exile On Main St. (Remastered)
     3. Highwayman
     4. Roll On (Bonus Track Version)
     5. Sleepless Nights
     6. The Essential Donovan
     7. Townes Van Zandt
     8. Skull Fu^H^H and Roses


**And the band keeps playing on...**
   -- John Perry Barlow


Motivation
----------

I have at least four avocado boxes of cd's in my basement, many of them
damaged by decades of shipping around the country without their cases.
A lot of them are ripped, and I also download live recordings thanks
to `bt.etree.org <http://bt.etree.org>`_ all the time.  All this data
has almost filled a terabyte cloud drive.  Plus it's scattered all over
a pile of old hard drives and home directory backups.  Finally, I want an
easy way to keep my old phone active as a stereo receiver via
`VLC <http://www.videolan.org/index.html>`_.

So, Tapedeck strives to organize this type of music collection and
provide a way for you to enjoy your music.


History
-------

I've had some scripts around for a while to manage my music, but I've never
built them into anything bigger partly because they require some complicated
programming techniques that I never really mastered.  Now that I have found
some `easier ways to program <http://github.com/python-trio/trio>`_ this
type of thing, I feel like I can put it all together into a nifty
`python <http://www.python.org>`_ package.


Requirements
------------

Mac
~~~

1. Install `Homebrew <http://brew.sh>`_ -
   "The missing package manager for macOS".

2. Install some handy programs that ``tapedeck`` requires::

   $ brew install python3 ffmpeg sox aria2 postgresql icecast2

Android
~~~~~~~

1. Install termux
2. Install deps

Windows
~~~~~~~

1. ``git clone http://github.com/zthompson47/tapedeck``
2. make it happen
3. let me know

iPhone
~~~~~~

1. refer
2. to
3. Windows


Sources
~~~~~~~

The source code for this project is hosted on both
`github <http://github.com/>`_ and `pypi <http://pypi.org>`_:

* `tapedeck on pypi <https://pypi.org/project/tapedeck/>`_
* `tapedeck on github <https://github.com/zthompson47/tapedeck>`_
* `reel on pypi <http://pypi.org/project/reel/>`_
* `reel on github <http://github.com/zthompson47/reel>`_
