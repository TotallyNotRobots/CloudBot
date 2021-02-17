from cloudbot.util.mapping import KeyFoldDict


class TestKeyFoldDict:
    @staticmethod
    def test_get():
        data = KeyFoldDict()
        data["TEST"] = 1

        assert data.get("TEST") == 1
        assert data.get("TeST") == 1
        assert data.get("test") == 1

    @staticmethod
    def test_setdefault():
        data = KeyFoldDict()

        data["test"] = 2

        assert data.setdefault("TEST", 1) == 2

        assert data["TEST"] == 2

        assert data.setdefault("STUFF", 5) == 5

        assert data["stuff"] == 5

    @staticmethod
    def test_update_kwargs():
        data = KeyFoldDict()

        data.update(a=1, B=2, vAR=3, VAL=4, mapping=5)

        assert data["a"] == 1
        assert data["A"] == 1
        assert data["b"] == 2
        assert data["B"] == 2
        assert data["var"] == 3
        assert data["vAr"] == 3
        assert data["VAR"] == 3
        assert data["val"] == 4
        assert data["VAL"] == 4
        assert data["Val"] == 4
        assert data["mapping"] == 5
        assert data["MAPPING"] == 5
        assert data["maPPiNg"] == 5

    @staticmethod
    def test_update_mapping():
        data = KeyFoldDict()

        data.update({"a": 1, "B": 2, "woRDs1": 3})

        assert data["a"] == 1
        assert data["A"] == 1
        assert data["b"] == 2
        assert data["B"] == 2
        assert data["words1"] == 3
        assert data["WORDS1"] == 3
        assert data["worDs1"] == 3

    @staticmethod
    def test_update_sequence():
        data = KeyFoldDict()

        data.update([("a", 1), ("B", 2), ("SEa", 3)])

        assert data["a"] == 1
        assert data["A"] == 1
        assert data["b"] == 2
        assert data["B"] == 2
        assert data["sea"] == 3
        assert data["SEA"] == 3
        assert data["SeA"] == 3
        assert data["Sea"] == 3
