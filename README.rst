====
reel
====

Async subprocess pipelines and stream transports::


   """An example of using ``reel`` to play music."""
   import trio

   from reel import Reel
   from reel.cmd import ffmpeg, sox


   async def main():
       """Play some audio files through the speakers."""
       cornell77 = ''.join([
           'http://archive.org/download/',
           'gd1977-05-08.shure57.stevenson.29303',
           '.flac16/gd1977-05-08d02t{}.flac'
       ])

       tracks = [
           'http://allotropic.com/static/out000.wav',
           'http://allotropic.com/static/out001.wav',
           'http://allotropic.com/static/out002.wav',
           'http://allotropic.com/static/out003.wav',
           'http://allotropic.com/static/out004.wav',
           'http://allotropic.com/static/out005.wav',
           cornell77.format('04'),
           cornell77.format('05'),
           'http://ice1.somafm.com/groovesalad-256-mp3',
       ]

       playlist = Reel([ffmpeg.read(track) for track in tracks])
       speakers = sox.speakers()

       async with playlist | speakers as player:
           await player.play()

   if __name__ == '__main__':
       trio.run(main)


Motivation
----------

This project is a simplified version of Python subprocess control with
pipes and asynchronous support.  It is being developed to support
`tapedeck <http://github.com/zthompson47/tapedeck>`_,
a music streaming package which uses ffmpeg and other shell commands to
get music from various sources to various destinations.
