#!/usr/bin/python

import logging
import optparse
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import musicbrainz2.disc as mbdisc
import musicbrainz2.utils as mbutil
import musicbrainz2.webservice as mbws

DEFAULT_DIR = ['/data/Music/test']
FLAC_OPTS = ['--best']
LAME_OPTS = ['--noreplaygain']
LAME_HIGH = ['--preset', 'extreme']
LAME_LOW  = ['--preset', 'medium']

def choose(name, items, fmt=str):
    if len(items) == 1:
        print "Found %s: %s" % (name, fmt(items[0]))
        return items[0]
    else:
        print '%ss:' % name
        for i, item in enumerate(items):
            print ' %2d. %s' % (i+1, fmt(item))
        choice = int(raw_input('Choose %s: ' % name))
        return items[choice - 1]

def thread_count():
    return os.sysconf('SC_NPROCESSORS_ONLN')

def parse_args():
    parser = optparse.OptionParser()
    parser.add_option('-d', '--device',
                      metavar='DEV', default='/dev/cdrom',
                      help='CD-ROM device path [%default]')
    parser.add_option('-D', '--directory',
                      metavar='DIR', default=DEFAULT_DIR,
                      help='Destination directory [%default]')
    parser.add_option('-t', '--threads', type='int',
                      metavar='NUM', default=thread_count(),
                      help='Number of worker threads [%default]')
    parser.add_option('--debug', action='store_true')

    group_p = optparse.OptionGroup(parser, "CD Paranoia Options")
    group_p.add_option('-Z', '--disable-paranoia', action='store_true')
    parser.add_option_group(group_p)

    #group_f = optparse.OptionGroup(parser, "FLAC Options")
    #group_f.add_option('--ogg', action='store_true')
    #parser.add_option_group(group_f)

    return parser.parse_args()

def worker(q):
    while True:
        task = q.get()
        task()
        q.task_done()

def main():
    opt, args = parse_args()

    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if opt.debug else logging.INFO)

    service = mbws.WebService()
    query = mbws.Query(service)

    print 'Reading %s TOC...' % opt.device
    disc = mbdisc.readDisc(opt.device)
    print 'Disk ID: %s\n' % disc.id

    print 'Searching for release info...'
    filter = mbws.ReleaseFilter(discId=disc.id)
    results = query.getReleases(filter)

    if not any(r.release.id for r in results):
        print 'No complete results found! Submit this CD to MusicBrainz:'
        print mbdisc.getSubmissionUrl(disc)
        return 1

    groups = {}

    for result in results:
        if not result.release.id:
            print result.release.__dict__
            continue
        include = mbws.ReleaseIncludes(artist=True,
                                       releaseEvents=True,
                                       releaseGroup=True)
        release = query.getReleaseById(result.release.id, include)
        group = groups.setdefault(release.releaseGroup.id,
                                  release.releaseGroup)
        group.addRelease(release)
        group.setArtist(release.artist)

    print 'Found %s releases in %s groups\n' % (len(results), len(groups))

    group = choose('Group', groups.values(),
                   lambda g: '%s - %s' % (g.artist.name, g.title))

    events = {}
    for release in group.releases:
        for event in release.releaseEvents:
            if event.format != event.FORMAT_CD:
                print 'What? %s' % event.format
                continue
            txt = '%-10s %s' % (event.date,
                                mbutil.getCountryName(event.country))
            events[txt] = release

    release = events[choose('Release', sorted(events))]

    inc = mbws.ReleaseIncludes(artist=True, tracks=True, releaseEvents=True)
    release = query.getReleaseById(release.getId(), inc)

    isSingleArtist = release.isSingleArtistRelease()

    for i, t in enumerate(release.tracks, 1):
        if isSingleArtist:
            title = t.title
        else:
            title = t.artist.name + ' - ' +  t.title

        (minutes, seconds) = t.getDurationSplit()
        print ' %2d. %s (%d:%02d)' % (i, title, minutes, seconds)

    if len(disc.tracks) != len(release.tracks):
        print 'Hmm... but the CD has %s tracks, now what?' % len(disc.tracks)
        return 1

    ok = raw_input('OK? [Y/n] ')
    if ok and ok[0].lower() not in ('y', 't', '1'):
        print 'Aborting...'
        return 1

    print 'Ripping...'
    tmp = tempfile.mkdtemp(prefix='pycde.')
    paranoia = ['--disable-paranoia'] if opt.disable_paranoia else []
    ret = subprocess.call(['cdparanoia', '-d', opt.device, '--batch']
                          + paranoia + ['1-', 'pycde.wav'], cwd=tmp)
    if ret != 0:
        print 'cdparanoia exited with code %d' % ret
        return 1

    shutil.rmtree(tmp)

if __name__ == '__main__':
    sys.exit(main())
