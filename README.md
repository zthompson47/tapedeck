# Tapedeck

A cli tool for organizing and enjoying music collections.

Just getting it started. Temporarily requires Linux and PulseAudio.

At least for now, it's an FFmpeg wrapper and requires `ffmpeg` in `PATH`.
The SQLite database is created in `$HOME/.local/share/tapedeck/tapedeck.db`.

### Basic Usage

```
$ tdsearch ~/tunes
$ tdsearch -l
1. ~/tunes/Greatest Hits Album
2. ~/tunes/Foxboro 90
$ tdplay -i 2
$ # then it's <i> for pager of text files in dir
$ #   (<j>/<k> scroll)
$ # <left>/<right> is next/prev
$ # <q> or <esc> or <ctrl-c> is quit
$ tdplay https://somafm.com/7soul.pls
```
