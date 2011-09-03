#!/usr/bin/python

import logging
import optparse
import os
import shutil
import subprocess
import sys
import tempfile
import threading

from pycde import error, textui, query


DEFAULT_DIR = ['/data/Music/test']
FLAC_OPTS = ['--best']
LAME_OPTS = ['--noreplaygain']
LAME_HIGH = ['--preset', 'extreme']
LAME_LOW  = ['--preset', 'medium']

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

    ui = textui.TextUI()
    q = query.Query(ui)

    release = q.get_release(opt.device)

    single_artist = release.is_single_artist()
    if len(release['medium-list']) != 1:
        ui.info('Disc %s' % release.disc['position'])

    def fmt_ms(ms):
        sec = int(ms) // 1000
        return '%d:%02d' % (sec // 60, sec % 60)

    for t in release.disc['track-list']:
        r = t['recording']
        if single_artist:
            title = r['title']
        else:
            title = '%(artist-credit-phrase)s - %(title)s' % r

        ui.info(' %2d. %s (%s)' %
                (int(t['position']), title, fmt_ms(r['length'])))

    ok = raw_input('OK? [Y/n] ')
    if ok and ok[0].lower() not in ('y', 't', '1'):
        raise error.Abort()

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
