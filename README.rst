====
reel
====

Async subprocess pipelines and stream transports::

   import reel

   tracks = ['track01', 'track02', 'http://w.w.w/track03']
   plst = reel.Reel(
       [reel.cmd.ffmpeg.read(_) for _ in tracks],
       announce_to=print
   )
   dest = reel.cmd.sox.speakers()
   norm = reel.cmd.ffmpeg.norm()
   vol = reel.cmd.ffmpeg.volume(1.0)

   async with plst | norm | vol | dest as transport:
       await transport.play()


Motivation
----------

This project is a simplified version of Python subprocess control with
pipes and asynchronous support.  It is being developed to support a music
streaming package which uses ffmpeg and other shell commands to get music
from various sources to various destinations.


Mythology
---------

The end goal is something like this::

   import reel


reel.Spool
~~~~~~~~~~


Logging
-------

``reel`` will log useful messages to a file called ``reel.log`` if you
configure a log level (e.g. bash)::

   $ export REEL_LOGGING_LEVEL='INFO'

That's all you need to set.

Available log levels, ranked by verbosity, with ``DEBUG`` the most
verbose, are:

* ``DEBUG`` - mostly useless information
* ``INFO`` - mostly useful information
* ``WARNING`` - might be a problem: suitable default for production
* ``ERROR`` - something bad happened
* ``CRITICAL`` - rare, show-stopping malfunction
* ``NOTSET`` - the default: no logging

By default, ``reel`` places the log file in ``$XDG_DATA_HOME``.  If
``$XDG_DATA_HOME`` is not set, ``reel`` chooses a suitable default
directory.  To view the choice, ask ``reel`` to print the current
configuration (e.g. bash)::

   $ reel --config | grep LOGGING

For direct control, explicitly set the logging directory with::

   $ export REEL_LOGGING_DIR='~/.local/share/reel'

In addition to sending useful information to ``reel.log``, you can ``reel`` also
logs output produced by subprocesses.  A subprocess can generate log files
in two ways:

1. The process might write it's own log file (e.g. a web server).

   In this case, ``reel`` might be able to control where the log file
   is written if the command is configured in ``reel.cmd``.  For example,
   ``reel.cmd.icecast`` will automatically write it's server log file
   to ``$REEL_LOGGING_DIR / icecast.log``.

2. You might decide to log stderr and/or stdout from a subprocess.

   You can decide what to do with any subprocess output, including
   logging it all to a file...

In general, ``reel`` attempts to keep all log files in one directory
and will sparingly create subdirectories if needed.
