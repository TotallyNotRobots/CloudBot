import weakref
from collections import defaultdict
from typing import TYPE_CHECKING, Generic, Optional, TypeVar, Union, cast

__all__ = (
    "KeyFoldDict",
    "KeyFoldMixin",
    "KeyFoldWeakValueDict",
    "DefaultKeyFoldDict",
)


K_contra = TypeVar("K_contra", bound=str, contravariant=True)
V = TypeVar("V")
T = TypeVar("T")


if TYPE_CHECKING:
    from typing import Protocol

    class MapBase(Protocol[K_contra, V]):
        def __getitem__(self, item: K_contra) -> V:
            ...

        def __delitem__(self, item: K_contra) -> None:
            ...

        def __setitem__(self, item: K_contra, value: V) -> None:
            ...

        def get(self, item: K_contra, default: V = None) -> Optional[V]:
            ...

        def setdefault(
            self, key: K_contra, default: Union[V, T] = None
        ) -> Union[V, T]:
            ...

        def pop(
            self, key: K_contra, default: Union[V, T] = None
        ) -> Union[V, T]:
            ...

else:

    class MapBase(Generic[K_contra, V]):
        ...


class KeyFoldMixin(MapBase[K_contra, V]):
    """
    A mixin for Mapping to allow for case-insensitive keys
    """

    def __getitem__(self, item: K_contra) -> V:
        return super().__getitem__(cast(K_contra, item.casefold()))

    def __setitem__(self, key: K_contra, value: V) -> None:
        return super().__setitem__(cast(K_contra, key.casefold()), value)

    def __delitem__(self, key: K_contra) -> None:
        return super().__delitem__(cast(K_contra, key.casefold()))

    def pop(self, key: K_contra, *args) -> V:
        """
        Wraps `dict.pop`
        """
        return super().pop(cast(K_contra, key.casefold()), *args)

    def get(self, key: K_contra, default=None):
        """
        Wrap `dict.get`
        """
        return super().get(cast(K_contra, key.casefold()), default)

    def setdefault(self, key: K_contra, default=None):
        """
        Wrap `dict.setdefault`
        """
        return super().setdefault(cast(K_contra, key.casefold()), default)

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
