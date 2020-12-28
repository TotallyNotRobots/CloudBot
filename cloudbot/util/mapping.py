import weakref
from collections import defaultdict

__all__ = (
    "KeyFoldDict",
    "KeyFoldMixin",
    "KeyFoldWeakValueDict",
    "DefaultKeyFoldDict",
)


# noinspection PyUnresolvedReferences
class KeyFoldMixin:
    """
    A mixin for Mapping to allow for case-insensitive keys
    """

    def __contains__(self, item):
        return super().__contains__(item.casefold())

    def __getitem__(self, item):
        return super().__getitem__(item.casefold())

    def __setitem__(self, key, value):
        return super().__setitem__(key.casefold(), value)

    def __delitem__(self, key):
        return super().__delitem__(key.casefold())

    def pop(self, key, *args, **kwargs):
        """
        Wraps `dict.pop`
        """
        return super().pop(key.casefold(), *args, **kwargs)

    def get(self, key, default=None):
        """
        Wrap `dict.get`
        """
        return super().get(key.casefold(), default)

    def setdefault(self, key, default=None):
        """
        Wrap `dict.setdefault`
        """
        return super().setdefault(key.casefold(), default)

    def update(self, *args, **kwargs):
        """
        Wrap `dict.update`
        """
        if args:
            mapping = args[0]
            if hasattr(mapping, "keys"):
                for k in mapping.keys():
                    self[k] = mapping[k]
            else:
                for k, v in mapping:
                    self[k] = v

        for k in kwargs:
            self[k] = kwargs[k]


class KeyFoldDict(KeyFoldMixin, dict):
    """
    KeyFolded dict type
    """


class DefaultKeyFoldDict(KeyFoldMixin, defaultdict):
    """
    KeyFolded defaultdict
    """


class KeyFoldWeakValueDict(KeyFoldMixin, weakref.WeakValueDictionary):
    """
    KeyFolded WeakValueDictionary
    """
