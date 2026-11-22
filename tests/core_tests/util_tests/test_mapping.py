from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from typing_extensions import override

from cloudbot.util.mapping import (
    DefaultKeyFoldDict,
    KeyFoldDict,
    KeyFoldWeakValueDict,
)

if TYPE_CHECKING:
    from collections.abc import MutableMapping


class C:
    pass


class BaseKeyFoldTest(ABC):
    @abstractmethod
    def get_class(self) -> type[MutableMapping[str, C]]:
        raise NotImplementedError

    def test_get(self) -> None:
        data = self.get_class()()
        data["TEST"] = c1 = C()

        assert data.get("TEST") == c1
        assert data.get("TeST") == c1
        assert data.get("test") == c1

    def test_setdefault(self) -> None:
        data = self.get_class()()

        data["test"] = c2 = C()
        c1 = C()
        assert data.setdefault("TEST", c1) == c2

        assert data["TEST"] == c2
        c5 = C()
        assert data.setdefault("STUFF", c5) == c5

        assert data["stuff"] == c5

    def test_delitem(self) -> None:
        data = self.get_class()()
        c1 = C()
        c2 = C()
        data.update(c1=c1, c2=c2)
        assert data == {"c1": c1, "c2": c2}
        del data["c1"]
        assert data == {"c2": c2}
        assert "c1" not in data

    def test_contains(self) -> None:
        data = self.get_class()()
        c1 = C()
        c2 = C()
        data.update(c1=c1, c2=c2)
        assert "c1" in data
        assert "C1" in data
        assert "C4" not in data
        assert 5 not in data

    def test_update_kwargs(self) -> None:
        data = self.get_class()()

        c1 = C()
        c2 = C()
        c3: C = C()
        c4 = C()
        c5 = C()
        data.update(a=c1, B=c2, vAR=c3, VAL=c4, mapping=c5)

        assert data["a"] == c1
        assert data["A"] == c1
        assert data["b"] == c2
        assert data["B"] == c2
        assert data["var"] == c3
        assert data["vAr"] == c3
        assert data["VAR"] == c3
        assert data["val"] == c4
        assert data["VAL"] == c4
        assert data["Val"] == c4
        assert data["mapping"] == c5
        assert data["MAPPING"] == c5
        assert data["maPPiNg"] == c5

    def test_update_mapping(self) -> None:
        data = self.get_class()()
        c1 = C()
        c2 = C()
        c3: C = C()

        data.update({"a": c1, "B": c2, "woRDs1": c3})

        assert data["a"] == c1
        assert data["A"] == c1
        assert data["b"] == c2
        assert data["B"] == c2
        assert data["words1"] == c3
        assert data["WORDS1"] == c3
        assert data["worDs1"] == c3

    def test_update_sequence(self) -> None:
        data = self.get_class()()
        c1 = C()
        c2 = C()
        c3: C = C()

        data.update([("a", c1), ("B", c2), ("SEa", c3)])

        assert data["a"] == c1
        assert data["A"] == c1
        assert data["A"] != c2
        assert data["b"] == c2
        assert data["B"] == c2
        assert data["sea"] == c3
        assert data["SEA"] == c3
        assert data["SeA"] == c3
        assert data["Sea"] == c3

    def test_compare_to_dict_literal(self) -> None:
        data = self.get_class()()
        c1 = C()

        data["A"] = c1

        assert data == {"a": c1}


class TestKeyFoldDict(BaseKeyFoldTest):
    @override
    def get_class(self) -> type[MutableMapping[str, Any]]:
        return KeyFoldDict


class TestKeyFoldDefaultDict(BaseKeyFoldTest):
    @override
    def get_class(self) -> type[MutableMapping[str, Any]]:
        return DefaultKeyFoldDict


class TestKeyFoldWeakValueDict(BaseKeyFoldTest):
    @override
    def get_class(self) -> type[MutableMapping[str, Any]]:
        return KeyFoldWeakValueDict
