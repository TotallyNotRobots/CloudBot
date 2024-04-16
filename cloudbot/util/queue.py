# A queue of objects that can be stacked and then popped and are dependent of user nick and channel

from threading import RLock
from typing import Iterable


class Dummy:
    def __getattribute__(self, item):
        try:
            return super().__getattribute__(item)
        except AttributeError:
            return None


class UserQueue(list):
    def __init__(self, _list: Iterable):
        super().__init__(_list)
        self._lock = RLock()
        self.metadata = Dummy()

    def pop(self):
        """Returns next item"""
        with self._lock:
            return super().pop(0)

    def append(self, item):
        """Appends item to the end of the queue"""
        with self._lock:
            super().append(item)

    def extend(self, items: Iterable):
        """Extends the queue with items"""
        with self._lock:
            super().extend(items)

    def set(self, items: Iterable):
        """Sets the queue to items"""
        with self._lock:
            super().clear()
            super().extend(items)


class ChannelQueue(dict):
    def __init__(self):
        super().__init__()
        self.metadata = Dummy()

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            super().__setitem__(key, UserQueue([]))
            return self[key]

    def __setitem__(self, key, value):
        if not isinstance(value, Iterable):
            raise TypeError(f"value must be iterable: {value=}")
        super().__setitem__(key, UserQueue(value))


class Queue(dict):
    """Queue that accepts 2 keys. Channel and user.
    q = Queue()
    q['#channel']['user'] = [1, 2, 3]
    q['#channel']['user'].pop()
    >> 1
    q['#channel']['user'].pop()
    >> 2
    """

    def __init__(self):
        super().__init__()
        self.metadata = Dummy()

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            super().__setitem__(key, ChannelQueue())
            return self[key]

    def __setitem__(self, key, value):
        raise TypeError("You may not set this directly")
