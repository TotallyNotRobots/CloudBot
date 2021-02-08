from unittest.mock import call

from irclib.parser import Message

from plugins.core import chan_key_db, server_info
from tests.util.mock_irc_client import MockIrcClient


def make_conn(mock_bot_factory, event_loop):
    bot = mock_bot_factory(loop=event_loop)
    conn = MockIrcClient(
        bot,
        "conn",
        "foobot",
        config={
            "connection": {
                "server": "host.invalid",
            },
        },
    )
    return conn


def test_load_keys(mock_bot_factory, mock_db, event_loop):
    conn = make_conn(mock_bot_factory, event_loop)
    db = mock_db.session()
    chan_key_db.table.create(mock_db.engine)
    mock_db.add_row(
        chan_key_db.table,
        conn=conn.name.lower(),
        chan="#foo",
        key="foobar",
    )
    assert chan_key_db.load_keys(conn, db) is None
    assert conn.get_channel_key("#foo") == "foobar"
    assert not conn.clear_channel_key("#bar")
    assert conn.get_channel_key("#foo") == "foobar"
    assert conn.clear_channel_key("#foo")
    assert conn.get_channel_key("#foo") is None


def test_handle_modes(mock_bot_factory, mock_db, event_loop):
    conn = make_conn(mock_bot_factory, event_loop)
    db = mock_db.session()
    chan_key_db.table.create(mock_db.engine)
    server_info.clear_isupport(conn)
    serv_info = server_info.get_server_info(conn)
    server_info.handle_prefixes("(YohvV)!@%+-", serv_info)
    server_info.handle_chan_modes(
        "IXZbegw,k,FHJLWdfjlx,ABCDKMNOPQRSTcimnprstuz", serv_info
    )
    assert (
        chan_key_db.handle_modes(["#foo", "+o", "foo"], conn, db, "#foo")
        is None
    )
    assert conn.get_channel_key("#foo") is None

    assert (
        chan_key_db.handle_modes(
            ["#foo", "+ok", "foo", "beep"], conn, db, "#foo"
        )
        is None
    )
    assert conn.get_channel_key("#foo") == "beep"

    assert (
        chan_key_db.handle_modes(
            ["#foo", "-ok", "foo", "beep"], conn, db, "#foo"
        )
        is None
    )
    assert conn.get_channel_key("#foo") is None

    assert (
        chan_key_db.handle_modes([conn.nick, "-ok"], conn, db, "server.host")
        is None
    )
    assert conn.get_channel_key("#foo") is None


def test_check_send_key(mock_bot_factory, mock_db, event_loop):
    conn = make_conn(mock_bot_factory, event_loop)
    db = mock_db.session()
    chan_key_db.table.create(mock_db.engine)
    msg = Message(None, None, "JOIN", ["#foo,#bar", "bing"])
    assert chan_key_db.check_send_key(conn, msg, db) is msg
    assert conn.get_channel_key("#foo") == "bing"

    msg = Message(None, None, "PRIVMSG", ["#foo,#bar", "bing"])
    assert chan_key_db.check_send_key(conn, msg, db) is msg

    msg = Message(None, None, "JOIN", ["#foo,#bar"])
    assert chan_key_db.check_send_key(conn, msg, db) is msg
    assert conn.get_channel_key("#foo") == "bing"


def test_key_use(mock_bot_factory, mock_db, event_loop):
    conn = make_conn(mock_bot_factory, event_loop)
    db = mock_db.session()
    chan_key_db.table.create(mock_db.engine)
    mock_db.add_row(
        chan_key_db.table,
        conn=conn.name.lower(),
        chan="#foo",
        key="foobar",
    )
    chan_key_db.load_keys(conn, db)
    conn.join("#foo")
    conn.join("#bar")
    assert conn.send.mock_calls == [call("JOIN #foo foobar"), call("JOIN #bar")]
