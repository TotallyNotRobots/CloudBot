from unittest.mock import MagicMock, call

import pytest

from plugins import grab
from tests.util.mock_conn import MockConn


def test_grab_add(mock_db):
    db = mock_db.session()
    grab.table.create(bind=mock_db.engine)
    grab.grab_add("foo", 123, "foobar", "#foo", db)
    assert mock_db.get_data(grab.table) == [("foo", "123", "foobar", "#foo")]


def test_grab_self(mock_db):
    grab.table.create(bind=mock_db.engine)
    conn = MockConn()
    db = mock_db.session()
    nick = "foo"
    res = grab.grab(nick, nick, "#foo", db, conn)
    assert res == "Didn't your mother teach you not to grab yourself?"


def test_grab_no_data(mock_db):
    grab.table.create(bind=mock_db.engine)
    conn = MockConn()
    db = mock_db.session()
    res = grab.grab("bar", "foo", "#foo", db, conn)
    assert res == "I couldn't find anything from bar in recent history."


def test_grab_duplicate(mock_db):
    grab.table.create(bind=mock_db.engine)
    nick = "foo"
    quote = "foo bar baz"
    chan = "#foo"
    target_nick = "bar"
    mock_db.add_row(
        grab.table, name=target_nick, time="123", quote=quote, chan=chan
    )
    conn = MockConn()
    conn.history[chan] = [
        (target_nick, 1234, quote),
    ]
    db = mock_db.session()
    grab.load_cache(db)
    res = grab.grab(target_nick, nick, chan, db, conn)
    assert res == "I already have that quote from {} in the database".format(
        target_nick
    )


def test_grab_error(mock_db, caplog_bot):
    nick = "foo"
    quote = "foo bar baz"
    chan = "#foo"
    target_nick = "bar"
    conn = MockConn()
    conn.history[chan] = [
        (target_nick, 1234, quote),
    ]
    grab.grab_cache.clear()
    db = mock_db.session()
    res = grab.grab(target_nick, nick, chan, db, conn)
    assert res == "Error occurred."
    assert caplog_bot.record_tuples == [
        ("cloudbot", 40, "Error occurred when grabbing bar in #foo")
    ]


@pytest.mark.parametrize(
    "nick,quote,out",
    [
        ("foo", "bar baz", "<f\u200boo> bar baz"),
        ("foo", "\1ACTION bar baz\1", "* f\u200boo bar baz"),
    ],
)
def test_format_grab(nick, quote, out):
    assert grab.format_grab(nick, quote) == out


def test_grabrandom_no_data():
    chan = "#foo"
    target_nick = "bar"
    grab.grab_cache.clear()
    event = MagicMock()
    res = grab.grabrandom(target_nick, chan, event.message)
    assert res == "I couldn't find any grabs in #foo."
    assert event.mock_calls == []


def test_grabrandom_no_data_no_text():
    chan = "#foo"
    grab.grab_cache.clear()
    grab.grab_cache[chan] = {"foo": []}
    event = MagicMock()
    res = grab.grabrandom("", chan, event.message)
    assert res == "I couldn't find any grabs in #foo."
    assert event.mock_calls == []


def test_grabrandom_no_text():
    chan = "#foo"
    grab.grab_cache.clear()
    grab.grab_cache[chan] = {"foo": ["bar baz"]}
    event = MagicMock()
    res = grab.grabrandom("", chan, event.message)
    assert res is None
    assert event.mock_calls == [call.message("<f\u200boo> bar baz")]


def test_grabsearch():
    chan = "#foo"
    grab.grab_cache.clear()
    grab.grab_cache[chan] = {"foo": ["bar baz"]}
    event = MagicMock()
    conn = MockConn()
    res = grab.grabsearch("bar", chan, conn)
    assert res == ["<f\u200boo> bar baz"]
    assert event.mock_calls == []


def test_last_grab_none(mock_db):
    chan = "#foo"
    text = "bar"
    grab.grab_cache.clear()
    grab.grab_cache[chan] = {text: []}
    event = MagicMock()
    res = grab.lastgrab(text, chan, event.message)
    assert res == "bar has never been grabbed."
    assert event.mock_calls == []


def test_last_grab_empty(mock_db):
    chan = "#foo"
    text = "bar"
    grab.grab_cache.clear()
    grab.grab_cache[chan] = {text: [""]}
    event = MagicMock()
    res = grab.lastgrab(text, chan, event.message)
    assert res is None
    assert event.mock_calls == []


def test_last_grab(mock_db):
    chan = "#foo"
    text = "bar"
    grab.grab_cache.clear()
    grab.grab_cache[chan] = {text: ["bar baz"]}
    event = MagicMock()
    res = grab.lastgrab(text, chan, event.message)
    assert res is None
    assert event.mock_calls == [call.message("<b\u200bar> bar baz", "#foo")]


def test_grabsearch_nick():
    chan = "#foo"
    grab.grab_cache.clear()
    target_nick = "foo"
    grab.grab_cache[chan] = {target_nick: ["bar baz"]}
    event = MagicMock()
    conn = MockConn()
    res = grab.grabsearch(target_nick, chan, conn)
    assert res == ["<f\u200boo> bar baz"]
    assert event.mock_calls == []
