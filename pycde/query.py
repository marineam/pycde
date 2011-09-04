#

"""Query MusicBrainz"""

import urllib2

from musicbrainz2 import disc
from pycde import error, musicbrainz


class ReleaseInfo(dict):

    include = ('artist-credits', 'labels', 'discids',
               'recordings', 'release-groups')

    def __init__(self, disc_id, release_id):
        self.disc_id = disc_id
        self.release_id = release_id
        info = musicbrainz.get_release_by_id(release_id, self.include)
        super(ReleaseInfo, self).__init__(info['release'])

        # Convert the list to a dict for easier access
        self.disc = self._get_disc()
        self.disc['track-dict'] = {}
        for t in self.disc['track-list']:
            i = int(t['position'])
            self.disc['track-dict'][i] = t

    def _get_disc(self):
        for m in self['medium-list']:
            for d in m['disc-list']:
                if d['id'] == self.disc_id:
                    return m
        raise ValueError('Disc ID %r not in release' % self.disc_id)

    def is_single_artist(self):
        def get_ids(obj):
            return set(a['artist']['id'] for a in obj['artist-credit']
                       if isinstance(a, dict))
        artists = get_ids(self)
        for m in self['medium-list']:
            for t in m['track-list']:
                t_artists = get_ids(t['recording'])
                if artists != t_artists:
                    return False
        return True


class Query(object):

    @classmethod
    def add_options(cls, parser):
        pass

    def __init__(self, opt, ui):
        self.ui = ui
        self.device = opt.device

    def get_disc(self):
        self.ui.status('Reading %s TOC...' % self.device)
        return disc.readDisc(self.device)

    def get_release(self, disc_info):
        self.ui.status('Disc ID: %s\n' % disc_info.id)
        self.ui.status('Searching for release info...')
        try:
            release_info = musicbrainz.get_releases_by_discid(
                    disc_info.id,
                    includes=['artists', 'recordings', 'labels'])
        except urllib2.HTTPError, ex:
            if ex.getcode() == 404:
                submit = disc.getSubmissionUrl(disc_info)
                self.ui.error('Release info not found!')
                self.ui.info('Submit info at: %s' % submit)
                raise error.Abort()
            raise

        releases = release_info['disc']['release-list']
        # Version 1 of the API provided partial results from
        # CDDB but I'm not sure about version 2 yet...
        assert all(r['id'] for r in releases)
        releases.sort(key=self._fmt_release)
        self.ui.status("Found %s possible release(s)" % len(releases))
        chosen = self.ui.choose('Release', releases, self._fmt_release)
        info = ReleaseInfo(disc_info.id, chosen['id'])

        # XXX: does the disc info include data tracks?
        if len(info.disc['track-list']) != len(disc_info.tracks):
            self.ui.error('Disc and metadata mismatch!')
            raise error.Abort()

        return info

    @staticmethod
    def _fmt_release(release):
        basics = ('artist-credit-phrase', 'title', 'date', 'country')
        fmt = ' - '.join(release[k] for k in basics if k in release)
        for label in release['label-info-list']:
            fmt += '\n%s' % label['label']['name']
            if 'catalog-number' in label:
                fmt += ' - %s' % label['catalog-number']
        if 'barcode' in release:
            fmt += '\nBarcode: %s' % release['barcode']
        return fmt
