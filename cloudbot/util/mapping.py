import weakref
from collections import defaultdict
from typing import Generic, Mapping, MutableMapping, Type, TypeVar, cast

__all__ = (
    "KeyFoldDict",
    "KeyFoldMixin",
    "KeyFoldWeakValueDict",
    "DefaultKeyFoldDict",
)


K = TypeVar("K", bound=str)
V = TypeVar("V")


class KeyFoldMixin(Generic[K, V]):
    """
    A mixin for Mapping to allow for case-insensitive keys
    """

    @classmethod
    def get_class(cls) -> Type[MutableMapping[K, V]]:
        raise NotImplementedError

    def __getitem__(self, item: K) -> V:
        return self.get_class().__getitem__(
            cast(Mapping[K, V], self), cast(K, item.casefold())
        )

    def __setitem__(self, key: K, value: V) -> None:
        return self.get_class().__setitem__(
            cast(MutableMapping[K, V], self), cast(K, key.casefold()), value
        )

    def __delitem__(self, key: K) -> None:
        return self.get_class().__delitem__(
            cast(MutableMapping[K, V], self), cast(K, key.casefold())
        )

    def pop(self, key: K, *args) -> V:
        """
        Wraps `dict.pop`
        """
        return self.get_class().pop(
            cast(MutableMapping[K, V], self), cast(K, key.casefold()), *args
        )

    def get(self, key: K, default=None):
        """
        Wrap `dict.get`
        """
        return self.get_class().get(
            cast(Mapping[K, V], self), cast(K, key.casefold()), default
        )

    def setdefault(self, key: K, default=None):
        """
        Wrap `dict.setdefault`
        """
        return self.get_class().setdefault(
            cast(MutableMapping[K, V], self), cast(K, key.casefold()), default
        )

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

    @classmethod
    def get_class(cls) -> Type[MutableMapping[K, V]]:
        return dict


class DefaultKeyFoldDict(KeyFoldMixin, defaultdict):
    """
    KeyFolded defaultdict
    """

    @classmethod
    def get_class(cls) -> Type[MutableMapping[K, V]]:
        return defaultdict


class KeyFoldWeakValueDict(KeyFoldMixin, weakref.WeakValueDictionary):
    """
    KeyFolded WeakValueDictionary
    """

    @classmethod
    def get_class(cls) -> Type[MutableMapping[K, V]]:
        return weakref.WeakValueDictionary
