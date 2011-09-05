#

"""Encode the data!"""

import threading
import Queue

from pycde import error


class Pool(object):

    _pool = None

    def __init__(self, threads):
        self.queue = Queue.Queue()
        self.mkjob = self._mkjob_method
        self.wait = self._wait_method
        for i in xrange(threads):
            thread = threading.Thread(target=self._worker)
            thread.daemon = True
            thread.start()

    def _worker(self):
        while True:
            task, args, kwargs = self.queue.get()
            try:
                task(*args, **kwargs)
            finally:
                self.queue.task_done()

    @classmethod
    def mkpool(cls, threads):
        if cls._pool is not None:
            return
        cls._pool = cls(threads)

    @classmethod
    def wait(cls):
        assert cls._pool is not None
        cls._pool.wait()

    @classmethod
    def mkjob(cls, task, *args, **kwargs):
        assert cls._pool is not None
        cls._pool.mkjob(task, *args, **kwargs)

    def _mkjob_method(self, task, *args, **kwargs):
        self.queue.put((task, args, kwargs))

    def _wait_method(self):
        self.queue.join()


class Encoder(object):

    @classmethod
    def add_options(cls, parser):
        pass

    def __init__(self, opt, ui):
        # Create singleton thread pool
        Pool.mkpool(opt.threads)
        self.opt = opt
        self.ui = ui

    def encode(self, track):
        Pool.mkjob(self._do_encode, track)

    def _do_encode(self, track):
        # Called in a thread to do the real work
        raise NotImplementedError()

    def tag(self, track, metadata):
        pass

    def _vorbis_tags(self, track, metadata):
        tags = []
        def tag(name, src, *keys):
            for key in keys:
                src = src.get(key, {})
            if isinstance(src, basestring):
                tags.append((name, src))

        def tag_list(src, *keys):
            for key in keys:
                src = src.get(key, {})
            if isinstance(src, list):
                return src
            else:
                return []

        def tag_str(src, *keys):
            for key in keys:
                src = src.get(key, {})
            if isinstance(src, basestring):
                return src

        track_data = metadata.disc['track-dict'][track]
        tag('TITLE', track_data, 'recording', 'title')
        tag('ALBUM', metadata, 'title')

        tids = set()
        for credit in tag_list(track_data, 'recording', 'artist-credit'):
            if isinstance(credit, basestring):
                continue
            tag('ARTIST', credit, 'artist', 'name')
            tids.add(tag_str(credit, 'artist', 'id'))

        ids = set(tag_str(c, 'artist', 'id') for c in
                  tag_list(metadata, 'artist-credit'))
        if tids != ids:
            for credit in tag_list(metadata, 'artist-credit'):
                if isinstance(credit, basestring):
                    continue
                tag('ALBUMARTIST', credit, 'artist', 'name')

        # Mark things as a compilation if the album artist
        # is not listed in the track artist list.
        # XXX: compute in the release metadata instead.
        if not ids.issubset(tids):
            tags.append(('COMPILATION', '1'))

        tag('DATE', metadata, 'date')
        orig = tag_str(metadata, 'release-group', 'first-release-date')
        if orig != metadata.get('date', None):
            tags.append(('ORIGINALDATE', orig))

        tags.append(('TRACKNUMBER', track_data['position']))
        tags.append(('TRACKTOTAL',  str(len(metadata.disc['track-dict']))))
        if len(metadata['medium-list']) != 1:
            tags.append(('DISCNUMBER', metadata.disc['position']))
            tags.append(('DISCTOTAL', str(len(metadata['medium-list']))))

        return tags

    def wait(self):
        Pool.wait()
