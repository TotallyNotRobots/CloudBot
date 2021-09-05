from unittest.mock import MagicMock, call

from plugins import admin_channel


def test_ban_no_char():
    event = MagicMock(chan="#bar")
    event.conn.memory = {"server_info": {}}
    admin_channel.ban("foo", event)
    assert event.mock_calls == [
        call.notice(
            "Mode character 'b' does not seem to exist on this network."
        )
    ]


def test_ban():
    event = MagicMock(chan="#bar", nick="test")
    event.conn.memory = {"server_info": {"channel_modes": "b"}}
    admin_channel.ban("foo", event)
    assert event.mock_calls == [
        call.notice("Attempting to ban foo in #bar..."),
        call.admin_log("test used ban to set +b on foo in #bar."),
        call.conn.send("MODE #bar +b foo"),
    ]


def test_ban_other_chan():
    event = MagicMock(chan="#bar", nick="test")
    event.conn.memory = {"server_info": {"channel_modes": "b"}}
    admin_channel.ban("#baz foo", event)
    assert event.mock_calls == [
        call.notice("Attempting to ban foo in #baz..."),
        call.admin_log("test used ban to set +b on foo in #baz."),
        call.conn.send("MODE #baz +b foo"),
    ]


def test_lock():
    event = MagicMock(chan="#bar", nick="test")
    event.conn.memory = {"server_info": {"channel_modes": "i"}}
    admin_channel.lock("", event)
    assert event.mock_calls == [
        call.notice("Attempting to lock #bar..."),
        call.admin_log("test used lock to set +i in #bar."),
        call.conn.send("MODE #bar +i"),
    ]


def test_quiet():
    event = MagicMock(chan="#bar", nick="test")
    event.conn.memory = {
        "server_info": {
            "channel_modes": "b",
            "extbans": "m",
            "extban_prefix": "",
        }
    }
    admin_channel.quiet("foo", event)
    assert event.mock_calls == [
        call.notice("Attempting to quiet m:foo in #bar..."),
        call.admin_log("test used quiet to set +b on m:foo in #bar."),
        call.conn.send("MODE #bar +b m:foo"),
    ]
