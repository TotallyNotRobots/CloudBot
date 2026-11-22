from __future__ import annotations

import weakref
from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol, TypeVar, cast, overload

from typing_extensions import override, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ("KeyFoldDict", "KeyFoldWeakValueDict", "DefaultKeyFoldDict")


K = TypeVar("K")

V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)

T = TypeVar("T")


@runtime_checkable
class SupportsKeysAndGetItem(Protocol[K, V_co]):  # pragma: no cover
    def keys(self) -> Iterable[K]: ...
    def __getitem__(self, key: K, /) -> V_co: ...


class KeyFoldDict(dict[str, V]):
    """
    KeyFolded dict type
    """

    @override
    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            item = item.casefold()

        return super().__contains__(item)

    @override
    def __getitem__(self, item: str) -> V:
        return super().__getitem__(item.casefold())

    @override
    def __setitem__(self, key: str, value: V) -> None:
        return super().__setitem__(key.casefold(), value)

    @override
    def __delitem__(self, key: str) -> None:
        return super().__delitem__(key.casefold())

    @overload
    def pop(self, key: str, /) -> V: ...

    @overload
    def pop(self, key: str, default: V, /) -> V: ...

    @overload
    def pop(self, key: str, default: T, /) -> V | T: ...

    @override
    def pop(self, key: str, /, *args: T | V) -> V | T:
        """
        Wraps `dict.pop`
        """
        return super().pop(key.casefold(), *args)

    @overload
    def get(self, key: str, default: None = None) -> V | None: ...

    @overload
    def get(self, key: str, default: V) -> V: ...

    @overload
    def get(self, key: str, default: T) -> V | T: ...

    @override
    def get(self, key: str, default: V | T | None = None) -> V | T | None:
        """
        Wrap `dict.get`
        """
        return super().get(key.casefold(), default)

    @override
    def setdefault(self, key: str, /, *args: V | None) -> V:
        """
        Wrap `dict.setdefault`
        """
        return super().setdefault(key.casefold(), cast("V", *args))

    @override
    def update(
        self,
        m: SupportsKeysAndGetItem[str, V] | Iterable[tuple[str, V]] = (),
        /,
        **kwargs: V,
    ) -> None:
        """
        Wrap `dict.update`
        """
        if isinstance(m, SupportsKeysAndGetItem):
            for k in m.keys():
                self[k] = m[k]
        else:
            for k, v in m:
                self[k] = v

        for k in kwargs:
            self[k] = kwargs[k]


class DefaultKeyFoldDict(defaultdict[str, V]):
    """
    KeyFolded defaultdict
    """

    @override
    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            item = item.casefold()

        return super().__contains__(item)

    @override
    def __getitem__(self, item: str) -> V:
        return super().__getitem__(item.casefold())

    @override
    def __setitem__(self, key: str, value: V) -> None:
        return super().__setitem__(key.casefold(), value)

    @override
    def __delitem__(self, key: str) -> None:
        return super().__delitem__(key.casefold())

    @overload
    def pop(self, key: str, /) -> V: ...

    @overload
    def pop(self, key: str, default: V, /) -> V: ...

    @overload
    def pop(self, key: str, default: T, /) -> V | T: ...

    @override
    def pop(self, key: str, /, *args: T | V) -> V | T:
        """
        Wraps `dict.pop`
        """
        return super().pop(key.casefold(), *args)

    @overload
    def get(self, key: str, default: None = None) -> V | None: ...

    @overload
    def get(self, key: str, default: V) -> V: ...

    @overload
    def get(self, key: str, default: T) -> V | T: ...

    @override
    def get(self, key: str, default: V | T | None = None) -> V | T | None:
        """
        Wrap `dict.get`
        """
        return super().get(key.casefold(), default)

    @override
    def setdefault(self, key: str, /, *args: V | None) -> V:
        """
        Wrap `dict.setdefault`
        """
        return super().setdefault(key.casefold(), cast("V", *args))

    @override
    def update(
        self,
        m: SupportsKeysAndGetItem[str, V] | Iterable[tuple[str, V]] = (),
        /,
        **kwargs: V,
    ) -> None:
        """
        Wrap `dict.update`
        """
        if isinstance(m, SupportsKeysAndGetItem):
            for k in m.keys():
                self[k] = m[k]
        else:
            for k, v in m:
                self[k] = v

        for k in kwargs:
            self[k] = kwargs[k]


class KeyFoldWeakValueDict(weakref.WeakValueDictionary[str, V]):
    """
    KeyFolded WeakValueDictionary
    """

    @override
    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            item = item.casefold()

        return super().__contains__(item)

    @override
    def __getitem__(self, item: str) -> V:
        return super().__getitem__(item.casefold())

    @override
    def __setitem__(self, key: str, value: V) -> None:
        return super().__setitem__(key.casefold(), value)

    @override
    def __delitem__(self, key: str) -> None:
        return super().__delitem__(key.casefold())

    @overload
    def pop(self, key: str, /) -> V: ...

    @overload
    def pop(self, key: str, default: V, /) -> V: ...

    @overload
    def pop(self, key: str, default: T, /) -> V | T: ...

    @override
    def pop(self, key: str, /, *args: T | V) -> V | T:
        """
        Wraps `dict.pop`
        """
        return super().pop(key.casefold(), *args)

    @overload
    def get(self, key: str, default: None = None) -> V | None: ...

    @overload
    def get(self, key: str, default: V) -> V: ...

    @overload
    def get(self, key: str, default: T) -> V | T: ...

    @override
    def get(self, key: str, default: V | T | None = None) -> V | T | None:
        """
        Wrap `dict.get`
        """
        return super().get(key.casefold(), default)

    @override
    def setdefault(self, key: str, default: V) -> V:
        """
        Wrap `dict.setdefault`
        """
        return super().setdefault(key.casefold(), default)

    @override
    def update(
        self,
        other: SupportsKeysAndGetItem[str, V]
        | Iterable[tuple[str, V]]
        | None = None,
        /,
        **kwargs: V,
    ) -> None:
        """
        Wrap `dict.update`
        """
        if other is not None:
            if isinstance(other, SupportsKeysAndGetItem):
                for k in other.keys():
                    self[k] = other[k]
            else:
                for k, v in other:
                    self[k] = v

        for k in kwargs:
            self[k] = kwargs[k]
