#!/usr/bin/env python
import os
import sys

def find_repository(start_dir):
    repository_names = [
        'cds',
        'shows',
        'torrents',
        'albums',
        'music',
        'audio',
        'itunes',
        'Podcasts',
        'tunes',
        'oink',
    ]
    dir = os.path.dirname(start_dir)
    while dir:
        for repository_name in repository_names:
            if dir.endswith(repository_name):
                return dir
        dir = os.path.dirname(dir)
    raise Exception("can't find repository:", start_dir)

exclude_dirs = [
    '.gaps',
]

music_exts = [
    '.flac',
    '.m4a',
    '.wav',
    '.shn',
    '.mov',
    '.mp3',
]

music_dirs = []
apple_dirs = []
mp3_dirs = []
random_dirs = []
repositories = []

# Walk through filesystem looking for music directories.
for root, dirs, files in os.walk('.'):
    for file in files:
        parent = os.path.dirname(os.path.join(root, file))
        for ext in music_exts:
            if file.endswith(ext):
                if '.m4a' == ext:
                    apple_dirs.append(parent)
                elif '.mp3' == ext:
                    mp3_dirs.append(parent)
                else:
                    try:
                        repositories.append(find_repository(parent))
                    except:
                        random_dirs.append(parent)
                        #print sys.exc_info()[1]
                        pass
                    else:
                        music_dirs.append(parent)

# Print each music directory.
repositories = list(set(repositories))
print '------------------------ repositories ---' + str(len(repositories))
for repository in repositories:
    print repository
random_dirs = list(set(random_dirs))
print '------------------------ random dirs ---' + str(len(random_dirs))
for random_dir in random_dirs:
    print random_dir
mp3_dirs = list(set(mp3_dirs))
print '------------------------ mp3 dirs ---' + str(len(mp3_dirs))
for mp3_dir in mp3_dirs:
    print mp3_dir
apple_dirs = list(set(apple_dirs))
print '------------------------ apple dirs ---' + str(len(apple_dirs))
for apple_dir in apple_dirs:
    print apple_dir
music_dirs = list(set(music_dirs))
print '------------------------ music dirs ---' + str(len(music_dirs))
for music_dir in music_dirs:
    if os.path.basename(music_dir) not in ['.gaps']:
        print music_dir
