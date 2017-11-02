from threading import Lock, Semaphore
from contextlib import contextmanager
from json import dump

class FakeLock:
    def lock_for_read(self):
        pass

    def unlock_for_read(self):
        pass

    @contextmanager
    def locked_for_read(self):
        yield

    @contextmanager
    def locked_for_write(self):
        yield

class ReaderWriterLock:
    def __init__(self):
        self.setlock = Lock()
        self.writelock = Lock()
        self.readcount = 0

    def lock_for_read(self):
        with locked(self.setlock):
            if self.readcount == 0:
                self.writelock.acquire()
            self.readcount += 1

    def unlock_for_read(self):
        with locked(self.setlock):
            self.readcount -= 1
            if self.readcount == 0:
                self.writelock.release()

    @contextmanager
    def locked_for_read(self):
        self.lock_for_read()
        yield
        self.unlock_for_read()

    @contextmanager
    def locked_for_write(self):
        with locked(self.writelock):
            yield

@contextmanager
def locked(lock):
    lock.acquire()
    yield
    lock.release()

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


def save(func):
    def func_wrapper(self, *args, **kwargs):
        retval = func(self, *args, **kwargs)
        with open(self.tmpfile, 'w') as f:
            dump({"queue": [self._current] + self.list}, f)
        return retval
    return func_wrapper

class Synced:
    def __init__(self):
        self._emptylock = Semaphore(0)
        self._writelock = Lock()
        self._readlock = Lock()
        self._readers = 0


class PreviewQueue(Synced):
    def __init__(self, tmpfile):
        super().__init__()
        self.list = []
        self._current = None
        self.tmpfile = tmpfile

    @decrease
    @write
    @save
    def get(self):
        self._current = self.list[0]
        del self.list[0]
        return self._current

    @increase
    @write
    @save
    def put(self, elem):
        self.list.append(elem)

    @read
    def get_list(self):
        return self.list

    @write
    def clear(self):
        while not self.list:
            self._emptylock.acquire()
            del self.list[0]

    @write
    @save
    def append(self, newlist):
        for item in newlist:
            self._emptylock.release()
            self.put(item)

    @write
    @save
    def move(self, src, dst):
        if len(self.list) < src:
            return
        self.list.insert(dst,self.list.pop(src))

    @decrease
    @write
    @save
    def delete(self, index):
        if len(self.list) < index:
            index = len(self.list) - 1
        del self.list[index]


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
