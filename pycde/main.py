#!/usr/bin/python

import logging
import optparse
import os
import shutil
import tempfile

from pycde import ripper, textui


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
    #query.Query.add_options(parser)
    ripper.Ripper.add_options(parser)

    opt, args = parser.parse_args()

    if args:
        tracks = []
        for i in args:
            try:
                i = int(i)
            except ValueError:
                parser.error('Invalid track number: %s' % i)
            if i < 1:
                parser.error('Invalid track number: %s' % i)
            tracks.append(i)
        tracks.sort()
    else:
        tracks = None

    return opt, tracks

def main():
    opt, tracks = parse_args()

    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if opt.debug else logging.INFO)

    ui = textui.TextUI()
    rip = ripper.Ripper(opt, tracks, ui)

    cwd = os.getcwd()
    tmp = tempfile.mkdtemp(prefix='pycde.')
    os.chdir(tmp)

    try:
        rip.rip()
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp)
