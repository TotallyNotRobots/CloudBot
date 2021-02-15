from unittest.mock import MagicMock

from cloudbot.util.irc import ChannelMode, ModeType, StatusMode
from plugins.core import server_info


def test_parse_isupport():
    conn = MagicMock(memory={})
    server_info.clear_isupport(conn)
    tokens = [
        "PREFIX=(ohv)@%+",
        "CHANMODES=a,b,c,d,e",
        "EXTBAN=$,abcd",
        "Foo=bar",
    ]
    params = ["foo"] + list(tokens) + ["blah"]
    server_info.on_isupport(conn, params)
    mode_a = ChannelMode("a", ModeType.A)
    mode_b = ChannelMode("b", ModeType.B)
    mode_c = ChannelMode("c", ModeType.C)
    mode_d = ChannelMode("d", ModeType.D)
    op = StatusMode.make("@", "o", 3)
    hop = StatusMode.make("%", "h", 2)
    voice = StatusMode.make("+", "v", 1)
    assert conn.memory == {
        "server_info": {
            "channel_modes": {
                "a": mode_a,
                "b": mode_b,
                "c": mode_c,
                "d": mode_d,
                "h": hop,
                "o": op,
                "v": voice,
            },
            "extban_prefix": "$",
            "extbans": "abcd",
            "isupport_tokens": {
                "CHANMODES": "a,b,c,d,e",
                "EXTBAN": "$,abcd",
                "FOO": "bar",
                "PREFIX": "(ohv)@%+",
            },
            "statuses": {
                "%": hop,
                "+": voice,
                "@": op,
                "h": hop,
                "o": op,
                "v": voice,
            },
        }
    }
