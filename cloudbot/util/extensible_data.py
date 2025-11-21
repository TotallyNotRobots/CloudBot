from contextlib import suppress
from typing import Any, Generic, TypeVar

_T = TypeVar("_T")


class Extensible:
    def __init__(self) -> None:
        self._exts = dict[ExtItem[Any], Any]()

    def clear_extents(self) -> None:
        self._exts.clear()

    def clear_ephemeral_extents(self) -> None:
        self._exts = {k: v for k, v in self._exts.items() if not k.ephemeral}


_extents = dict[str, "ExtItem[Any]"]()


class ExtItem(Generic[_T]):
    def __init__(self, name: str, *, ephemeral: bool = False) -> None:
        self.name = name
        self.ephemeral = ephemeral
        if self.name in _extents:
            raise ValueError(f"Duplicate extent registration {self.name}")

        _extents[self.name] = self

    def has(self, ext: Extensible) -> bool:
        return self in ext._exts

    def get(self, ext: Extensible) -> _T | None:
        return ext._exts.get(self)

    def ensure(self, ext: Extensible) -> _T:
        out = self.get(ext)
        if out is None:
            out = self.create()
            self.set(ext, out)

        return out

    def set(self, ext: Extensible, value: _T | None) -> None:
        if value is None:
            self.clear(ext)
        else:
            ext._exts[self] = value

    def clear(self, ext: Extensible) -> None:
        with suppress(KeyError):
            del ext._exts[self]

    def create(self) -> _T:
        raise NotImplementedError
