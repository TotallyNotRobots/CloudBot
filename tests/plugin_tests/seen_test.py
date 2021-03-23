from unittest.mock import MagicMock

from cloudbot.event import CommandEvent, Event, EventType
from plugins import seen
from tests.util.mock_conn import MockConn


def test_seen_track_correction(mock_db, freeze_time):
    seen.table.create(mock_db.engine)
    db = mock_db.session()
    conn = MockConn()
    event = Event(
        conn=conn,
        channel="#foo",
        content="s/a/b/",
        nick="bar",
        event_type=EventType.message,
    )
    res = seen.chat_tracker(event, db)
    assert res is None
    assert mock_db.get_data(seen.table) == []


def test_seen_track_pm(mock_db, freeze_time):
    seen.table.create(mock_db.engine)
    db = mock_db.session()
    conn = MockConn()
    event = Event(
        conn=conn,
        channel="foo",
        content="foo",
        nick="bar",
        event_type=EventType.message,
    )
    res = seen.chat_tracker(event, db)
    assert res is None
    assert mock_db.get_data(seen.table) == []


def test_seen_track(mock_db, freeze_time):
    seen.table.create(mock_db.engine)
    db = mock_db.session()
    conn = MockConn()
    event = Event(
        conn=conn,
        channel="#foo",
        content="foo",
        nick="bar",
        event_type=EventType.message,
    )
    res = seen.chat_tracker(event, db)
    assert res is None
    assert mock_db.get_data(seen.table) == [
        ("bar", 1566497676.0, "foo", "#foo", "None")
    ]


def test_seen_track_update(mock_db, freeze_time):
    seen.table.create(mock_db.engine)
    nick = "bar"
    chan = "#foo"
    mock_db.add_row(
        seen.table,
        name=nick,
        time=123,
        quote="foo",
        chan=chan,
        host="foo.bar",
    )
    assert mock_db.get_data(seen.table) == [
        ("bar", 123.0, "foo", "#foo", "foo.bar")
    ]
    db = mock_db.session()
    conn = MockConn()
    event = Event(
        conn=conn,
        channel=chan,
        content="foo",
        nick=nick,
        event_type=EventType.message,
    )
    res = seen.chat_tracker(event, db)
    assert res is None
    assert mock_db.get_data(seen.table) == [
        ("bar", 1566497676.0, "foo", "#foo", "None")
    ]


def test_seen_track_action(mock_db, freeze_time):
    seen.table.create(mock_db.engine)
    db = mock_db.session()
    conn = MockConn()
    event = Event(
        conn=conn,
        channel="#foo",
        content="foo",
        nick="bar",
        event_type=EventType.action,
    )
    res = seen.chat_tracker(event, db)
    assert res is None
    assert mock_db.get_data(seen.table) == [
        ("bar", 1566497676.0, "\x01ACTION foo\x01", "#foo", "None")
    ]


def test_seen_bot(mock_db, freeze_time):
    db = mock_db.session()
    conn = MockConn()
    event = CommandEvent(
        conn=conn,
        channel="#foo",
        content="foo",
        nick="bar",
        hook=MagicMock(),
        text=conn.nick,
        triggered_command="seen",
        cmd_prefix=".",
    )
    res = seen.seen(event.text, event.nick, event.chan, db, event)
    assert res == "You need to get your eyes checked."


def test_seen_self(mock_db, freeze_time):
    db = mock_db.session()
    conn = MockConn()
    nick = "bar"
    event = CommandEvent(
        conn=conn,
        channel="#foo",
        content="foo",
        nick=nick,
        hook=MagicMock(),
        text=nick,
        triggered_command="seen",
        cmd_prefix=".",
    )
    res = seen.seen(event.text, event.nick, event.chan, db, event)
    assert res == "Have you looked in a mirror lately?"


def test_seen_not_seen(mock_db, freeze_time):
    seen.table.create(mock_db.engine)
    db = mock_db.session()
    conn = MockConn()
    nick = "bar"
    event = CommandEvent(
        conn=conn,
        channel="#foo",
        content="foo",
        nick=nick,
        hook=MagicMock(),
        text="other",
        triggered_command="seen",
        cmd_prefix=".",
    )
    res = seen.seen(event.text, event.nick, event.chan, db, event)
    assert res == "I've never seen other talking in this channel."


def test_seen(mock_db, freeze_time):
    seen.table.create(mock_db.engine)
    chan = "#foo"
    mock_db.add_row(
        seen.table,
        name="other",
        time=123,
        quote="foo",
        chan=chan,
        host="foo.bar",
    )

    db = mock_db.session()
    conn = MockConn()
    nick = "bar"
    event = CommandEvent(
        conn=conn,
        channel=chan,
        content="foo",
        nick=nick,
        hook=MagicMock(),
        text="other",
        triggered_command="seen",
        cmd_prefix=".",
    )
    res = seen.seen(event.text, event.nick, event.chan, db, event)
    assert res == "other was last seen 49 years and 8 months ago saying: foo"


def test_seen_bad_nick(mock_db, freeze_time):
    seen.table.create(mock_db.engine)
    chan = "#foo"
    mock_db.add_row(
        seen.table,
        name="other",
        time=123,
        quote="foo",
        chan=chan,
        host="foo.bar",
    )

    db = mock_db.session()
    conn = MockConn()
    conn.is_nick_valid = lambda text: False  # type: ignore[assignment]
    nick = "bar"
    event = CommandEvent(
        conn=conn,
        channel=chan,
        content="foo",
        nick=nick,
        hook=MagicMock(),
        text="other",
        triggered_command="seen",
        cmd_prefix=".",
    )

    res = seen.seen(event.text, event.nick, event.chan, db, event)
    assert res == "I can't look up that name, its impossible to use!"


def test_seen_action(mock_db, freeze_time):
    seen.table.create(mock_db.engine)
    chan = "#foo"
    mock_db.add_row(
        seen.table,
        name="other",
        time=123,
        quote="\1ACTION foobar\1",
        chan=chan,
        host="foo.bar",
    )

    db = mock_db.session()
    conn = MockConn()
    nick = "bar"
    event = CommandEvent(
        conn=conn,
        channel=chan,
        content="foo",
        nick=nick,
        hook=MagicMock(),
        text="other",
        triggered_command="seen",
        cmd_prefix=".",
    )
    res = seen.seen(event.text, event.nick, event.chan, db, event)
    assert (
        res == "other was last seen 49 years and 8 months ago: * other foobar"
    )
