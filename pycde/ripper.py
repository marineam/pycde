#

"""Rip the data!"""

import optparse
import subprocess

from pycde import error, flac, query, replaygain


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

    def rip(self):
        self.metadata = self._get_metadata()
        self._pre_summary()

        if not self.ui.yesno('OK?'):
            raise error.Abort()

        analyzer = replaygain.ReplayGain()
        encoders = [flac.FlacEncoder(self.opt, self.ui)]

        for track in self.tracks:
            track_data = self.metadata.disc['track-dict'][track]
            self.ui.status('Ripping track %02d. %s...' %
                           (track, track_data['recording']['title']))
            path = self._rip_track(track)
            track_gain = analyzer.analyze_track(path)
            track_data['replaygain-track-gain'] = track_gain.gain
            track_data['replaygain-track-peak'] = track_gain.peak
            self.ui.status('Encoding track %02d. %s...' %
                           (track, track_data['recording']['title']))
            for encoder in encoders:
                encoder.encode(track)

        album_gain = analyzer.analyze_album()
        self.metadata['replaygain-album-gain'] = album_gain.gain
        self.metadata['replaygain-album-peak'] = album_gain.peak
        self.metadata['replaygain-reference-loudness'] = \
                replaygain.REFERENCE_LOUDNESS

        self.ui.status('Waiting for encoder(s) to finish...')
        for encoder in encoders:
            encoder.wait()

        for track in self.tracks:
            track_data = self.metadata.disc['track-dict'][track]
            self.ui.status('Tagging track %02d. %s...' %
                           (track, track_data['recording']['title']))
            for encoder in encoders:
                encoder.tag(track, self.metadata)

        import pprint, os
        pprint.pprint(self.metadata)
        os.system("ls -la")

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
