# Tapedeck

A cli tool for organizing and enjoying music collections.

Just getting this version started. Temporarily requires Linux and PulseAudio.

At least for now, it's an FFmpeg wrapper and requires `ffmpeg` in `PATH`.
The SQLite database is `$HOME/.local/share/tapedeck/tapedeck.db`.

### Basic Usage

```
$ tdsearch ~/tunes
$ tdsearch -l
1. ~/tunes/albums/Greatest Hits
2. ~/tunes/shows/gd1973-05-26-kezar.shnf
3. ~/tunes/shows/gd1977-05-18-barton.flacf
4. ~/tunes/shows/Foxboro '90
$ tdplay -i 4
$ # <left>/<right> next/prev
$ # <q> | <esc> | <ctrl-c> quit
$ # <i> pager of text files in dir
$ #   <j>/<k> scroll
$ tdplay https://somafm.com/7soul.pls
```
