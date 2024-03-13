from cloudbot.util import irc


def test_mode_parse():
    mode_info = {
        "a": irc.ChannelMode(character="a", type=irc.ModeType.A),
        "d": irc.StatusMode.make("^", "d", 3),
    }
    parsed = irc.parse_mode_string("+ad", ["foo", "bar"], mode_info)

    assert parsed == [
        irc.ModeChange("a", True, "foo", mode_info["a"]),
        irc.ModeChange("d", True, "bar", mode_info["d"]),
    ]


def test_mode_parse_missing_mode():
    mode_info = {
        "a": irc.ChannelMode(character="a", type=irc.ModeType.A),
        "d": irc.StatusMode.make("^", "d", 3),
    }
    parsed = irc.parse_mode_string("+adx", ["foo", "bar"], mode_info)

    assert parsed == [
        irc.ModeChange("a", True, "foo", mode_info["a"]),
        irc.ModeChange("d", True, "bar", mode_info["d"]),
        irc.ModeChange("x", True, None, None),
    ]

    assert [m.is_status for m in parsed] == [False, True, False]
