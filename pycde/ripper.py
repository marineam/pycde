#

"""Rip the data!"""

import optparse
import subprocess

from pycde import error, query, replaygain


class Ripper(object):

    @classmethod
    def add_options(cls, parser):
        group_p = optparse.OptionGroup(parser, "CD Paranoia Options")
        group_p.add_option('-Z', '--disable-paranoia', action='store_true')
        group_p.add_option('-X', '--abort-on-skip', action='store_true')
        parser.add_option_group(group_p)

    def __init__(self, opt, tracks, ui):
        self.ui = ui
        self.opt = opt
        self.tracks = tracks
        self.metadata = None
        self.track_gain = {}
        self.album_gain = None

    def rip(self):
        self.metadata = self._get_metadata()
        self._pre_summary()

        if not self.ui.yesno('OK?'):
            raise error.Abort()

        analyzer = replaygain.ReplayGain()

        for track in self.tracks:
            path = self._rip_track(track)
            gain = analyzer.analyze_track(path)
            self.track_gain[path] = gain

        self.album_gain = analyzer.analyze_album()
        import pprint
        pprint.pprint(self.track_gain)
        pprint.pprint(self.album_gain)

    def _get_metadata(self):
        q = query.Query(self.opt, self.ui)
        disc = q.get_disc()

        if self.tracks:
            last = len(disc.tracks)
            bad = [str(i) for i in xrange(len(disc.tracks)) if i > last]
            if bad:
                self.ui.error('Invalid track numbers: %s' % ' '.join(bad))
                raise error.Abort()
        else:
            self.tracks = range(len(disc.tracks))

        return q.get_release(disc)

    def _pre_summary(self):
        if len(self.metadata['medium-list']) != 1:
            self.ui.info('Disc %s' % self.metadata.disc['position'])

        single_artist = self.metadata.is_single_artist()
        for track in self.metadata.disc['track-list']:
            index = int(track['position'])
            if index not in self.tracks:
                continue

            rec = track['recording']
            if single_artist:
                title = rec['title']
            else:
                title = '%(artist-credit-phrase)s - %(title)s' % rec

            sec = int(rec['length']) // 1000
            self.ui.info(' %2d. %s (%d:%02d)' %
                    (index, title, sec // 60, sec % 60))

    def _rip_track(self, track):
        path = 'track%02d.wav' % track
        cmd = ['cdparanoia', '-d', self.opt.device]
        if self.opt.disable_paranoia:
            cmd.append('--disable-paranoia')
        if self.opt.abort_on_skip:
            cmd.append('--abort-on-skip')
        cmd.append(str(track))
        cmd.append(path)
        ret = subprocess.call(cmd)
        if ret != 0:
            self.ui.error('cdparanoia exited with code %d' % ret)
            raise error.Abort()
        return path
