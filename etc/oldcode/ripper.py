import os
import sys
from datetime import datetime
import subprocess
#from pipes import quote
#import pickle

from mutagen.flac import FLAC
import DiscID
import CDDB
#from django.conf import settings
#from django.utils.encoding import DjangoUnicodeDecodeError

#from tapedeck.models import Album, Track

CD_DIR = '/home/zach/td_work/cds'

def convert_to_unicode(string):
    try:
        string = unicode(string)
    except UnicodeDecodeError:
        try:
            string = string.decode('latin-1')
        except UnicodeDecodeError:
            string = string.decode('utf-8', 'replace')
    return string

def rip():

    # Get CDDB info.
    device = DiscID.open()
    disc_id = DiscID.disc_id(device)
    (query_status, query_info) = CDDB.query(disc_id)

    # Check for multiple entries.
    # FIXME - hmm tell CDDB not to prompt me for this..  not sure what's up..  Air - Talkie Walkie
    if query_status == 211 or query_status == 210:
        # 211 - multiple inexact matches
        # 210 - multiple exact matches
        query_info = query_info[1]
    
    #print pickle.dumps(query_info)
    #sys.exit()

    (read_status, read_info) = CDDB.read(query_info['category'], query_info['disc_id'])
    if read_status != 210:
        print "Can't find disc in CDDB."
        sys.exit()
  
    # Create named directories.
    (artist, title) = read_info['DTITLE'].split(' / ')
    artist = convert_to_unicode(artist)
    title = convert_to_unicode(title)

    #artist_dir = "%s/%s" % (settings.TD_CD_DIR, artist)
    artist_dir = "%s/%s" % (CD_DIR, artist.replace('/', '-'))
    album_dir = "%s/%s" % (artist_dir, title.replace('/', '-'))
    gaps_dir = "%s/.gaps" % album_dir
    if os.access(artist_dir, os.F_OK) == False:
        os.mkdir(artist_dir)
    if os.access(album_dir, os.F_OK) == False:
        os.mkdir(album_dir)
    if os.access(gaps_dir, os.F_OK) == False:
        os.mkdir(gaps_dir)

    track_count = disc_id[1]
    genre = ''
    try:
        genre = read_info['DGENRE']
    except:
        pass
    if genre == '':
        genre = query_info['category']

#    # TODO - Save record of album.
#    album = Album(
#        title = title,
#        artist = artist,
#        year = read_info['DYEAR'],
#        genre = genre,
#        save_dir = album_dir,
#        cddb_disc_id = query_info['disc_id'],
#        cddb_disc_category = query_info['category'],
#        track_count = track_count,
#        created_at = datetime.now(),
#        updated_at = datetime.now(),
#    )
#
#    album.save()

    # Rip CD.
    os.chdir(album_dir)
    subprocess.call(['/usr/local/bin/cdparanoia', '-O 102', '-v', '-w', '1-', 'data.wav'])

    # Create TOC.
    os.system('/usr/bin/cdrdao read-toc --datafile data.wav --with-cddb --read-subchan rw data.toc')

    os.system('/usr/bin/toc2cue data.toc data.cue')
# FIXME
# got random error from lines with: DISC_ID ''
#
#toc2cue version 1.2.2 - (C) Andreas Mueller <andreas@daneb.de>
#
#ERROR: data.toc:31: Invalid CD-TEXT item for a track.
#ERROR: data.toc:49: Invalid CD-TEXT item for a track.
#ERROR: data.toc:67: Invalid CD-TEXT item for a track.
#ERROR: Failed to read toc-file 'data.toc'.

    os.system('/usr/bin/cuebreakpoints --split-gaps data.cue | /usr/bin/shnsplit -o wav data.wav')

    # Figure out which files are tracks and which are pregaps.
    track = 1
    real_track = 1
    for line in open('data.cue', 'r').readlines():
        line = line.rstrip().lstrip()
        if line.startswith('INDEX 01'):
            print "audio - %s - %s" % (track, real_track)
            infile = "split-track%02d.wav" % track
            outfile = "track%02d.cdda.wav" % real_track
            os.rename(infile, outfile)
            real_track += 1
        elif line.startswith('INDEX 00'):
            infile = "split-track%02d.wav" % track
            #os.remove(infile)
            outfile = ".gaps/gap%02d.wav" % real_track
            os.rename(infile, outfile)
            subprocess.call(['/usr/bin/flac', '-8', '--delete-input-file', outfile])
            print "pregap - %s - %s" % (track, real_track)
        else:
            continue
        track += 1

    # Save tracks.
    outfiles = []
    for i in range(track_count):

        track_title = read_info["TTITLE%d" % i]
        track_title = convert_to_unicode(track_title)

        # Compress track.
        infile = "track%02d.cdda.wav" % (i + 1)
        outfile = (("%02d - " % (i + 1)) + track_title + ".wav").replace('/', '-')
        outfile2 = (("%02d - " % (i + 1)) + track_title + ".flac").replace('/', '-')
        outfiles.append(outfile2)
        os.rename(infile, outfile)
        subprocess.call(['/usr/bin/flac', '-8', '--delete-input-file', outfile])

        save_file = "%s/%s" % (album_dir, outfile2)

#        # Save record of track.
#        track = Track(
#            title = track_title,
#            album = album,
#            number = i + 1,
#            save_file = save_file,
#            created_at = datetime.now(),
#            updated_at = datetime.now(),
#        )
#        track.save()

        to_tag = FLAC(save_file)
        to_tag['artist'] = artist
        to_tag['genre'] = genre
        to_tag['album'] = title
        to_tag['title'] = track_title
        to_tag['tracknumber'] = "%d" % (i + 1)
        try:
            to_tag['date'] = read_info['DYEAR']
        except:
            pass
        to_tag.save()
    os.remove('data.wav')
