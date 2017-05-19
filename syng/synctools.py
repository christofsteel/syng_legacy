from threading import Lock, Semaphore


def write(func):
    def func_wrapper(self, *args, **kwargs):
        self._writelock.acquire()
        retval = func(self, *args, **kwargs)
        self._writelock.release()
        return retval
    return func_wrapper


def decrease(func):
    def func_wrapper(self, *args, **kwargs):
        self._emptylock.acquire()
        return func(self, *args, **kwargs)
    return func_wrapper


def increase(func):
    def func_wrapper(self, *args, **kwargs):
        retval = func(self, *args, **kwargs)
        self._emptylock.release()
        return retval
    return func_wrapper


def read(func):
    def func_wrapper(self, *args, **kwargs):
        self._readlock.acquire()
        if self._readers == 0:
            self._writelock.acquire()
        self._readers += 1
        self._readlock.release()
        retval = func(self, *args, **kwargs)
        self._readlock.acquire()
        self._readers -= 1
        if self._readers == 0:
            self._writelock.release()
        self._readlock.release()
        return retval
    return func_wrapper


class Synced:
    def __init__(self):
        self._emptylock = Semaphore(0)
        self._writelock = Lock()
        self._readlock = Lock()
        self._readers = 0


class PreviewQueue(Synced):
    def __init__(self):
        super().__init__()
        self.list = []

    @decrease
    @write
    def get(self):
        element = self.list[-1]
        del self.list[-1]
        return element

    @increase
    @write
    def put(self, elem):
        self.list.append(elem)

    @read
    def get_list(self):
        return self.list


class SyncedAtom(Synced):
    def __init__(self, item):
        super().__init__()
        self.item = item

    @write
    def set(self, item):
        self.item = item

    @read
    def get(self):
        return self.item
