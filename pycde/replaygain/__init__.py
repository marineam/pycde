#

"""Python bindings for ReplayGain.

The library can only handle one album at a time and I'm not going
to bother trying to make it thread safe. So all access should be
through this Python API and not the _gain module so it can be
protected with a mutex.
"""

import threading
from collections import namedtuple

from pycde.replaygain import _gain

REFERENCE_LOUDNESS = _gain.REFERENCE_LOUDNESS

class ReplayGainError(Exception):
    """Generic error"""

GainPeak = namedtuple('GainPeak', 'gain peak')

class ReplayGain(object):
    """ReplayGain analyzer for a single album.

    Note: due to limitations of the swiped C code only one album
    can be analyzed at a time. After creating a ReplayGain object
    it is impossible to create another until after analyze_album()
    has been called on the first which finalizes the processing.
    """

    _lock = threading.Lock()

    def __init__(self):
        self.tracks = []
        self.album = None
        self._done = False
        self._lock.acquire()
        try:
            _gain.clear()
        except _gain.GainError, ex:
            raise ReplayGainError(str(ex))

    def __del__(self):
        if not self._done:
            self._lock.release()

    def analyze_track(self, track):
        """Read and analyze a given track, get gain and peak.

        :param track: source audio file
        :type track: file-like object or path to file
        :return: tuple of the suggested gain and peak value
        :rtype: (float, float)
        """
        assert not self._done

        if isinstance(track, basestring):
            name = track
            close_track = True
            track = open(name, 'r')
        else:
            name = track.name
            close_track = False

        try:
            result = GainPeak(*_gain.track(track.fileno()))
        except _gain.GainError, ex:
            raise ReplayGainError('%s: %s' % (name, ex))

        if close_track:
            track.close()

        self.tracks.append(result)
        return result

    def analyze_album(self):
        """Finalize the album analysis, get gain and peak.

        Note: After calling this method neither analyze_track nor
        analyze_album can be called again but the object attributes
        are still available.

        :return: tuple of the suggested gain and peak value
        :rtype: (float, float)
        """
        assert not self._done

        try:
            self.album = GainPeak(*_gain.album())
        except _gain.GainError, ex:
            raise ReplayGainError(str(ex))

        self._done = True
        self._lock.release()

        return self.album
