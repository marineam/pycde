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

    def tag(self, track, metadata):
        pass

    def _do_encode(self, track):
        # Called in a thread to do the real work
        raise NotImplementedError()

    def wait(self):
        Pool.wait()
