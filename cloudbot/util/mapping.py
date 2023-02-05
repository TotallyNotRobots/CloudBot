import weakref
from collections import defaultdict
from typing import TYPE_CHECKING, Generic, MutableMapping, TypeVar, cast

__all__ = (
    "KeyFoldDict",
    "KeyFoldMixin",
    "KeyFoldWeakValueDict",
    "DefaultKeyFoldDict",
)


K = TypeVar("K", bound=str)
V = TypeVar("V")

if TYPE_CHECKING:

    class MapBase(MutableMapping[K, V]):
        ...

else:

    class MapBase(Generic[K, V]):
        ...


class KeyFoldMixin(MapBase[K, V]):
    """
    A mixin for Mapping to allow for case-insensitive keys
    """

    def __getitem__(self, item: K) -> V:
        return super().__getitem__(cast(K, item.casefold()))

    def __setitem__(self, key: K, value: V) -> None:
        return super().__setitem__(cast(K, key.casefold()), value)

    def __delitem__(self, key: K) -> None:
        return super().__delitem__(cast(K, key.casefold()))

    def pop(self, key: K, *args) -> V:
        """
        Wraps `dict.pop`
        """
        return super().pop(cast(K, key.casefold()), *args)

    def get(self, key: K, default=None):
        """
        Wrap `dict.get`
        """
        return super().get(cast(K, key.casefold()), default)

    def setdefault(self, key: K, default=None):
        """
        Wrap `dict.setdefault`
        """
        return super().setdefault(cast(K, key.casefold()), default)

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
