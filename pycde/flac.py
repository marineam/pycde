#

"""Encode flac!"""

import subprocess

from pycde import encoder, error


class FlacEncoder(encoder.Encoder):

    FLAC = ['flac', '--best', '--silent']

    def _do_encode(self, track):
        src = 'track%02d.wav' % track
        dst = 'track%02d.flac' % track
        ret = subprocess.call(self.FLAC + ['-o', dst, src])
        if ret != 0:
            self.ui.error('flac exited with code %d' % ret)
            raise error.Abort()
