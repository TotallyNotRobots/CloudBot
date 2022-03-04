import datetime
from unittest.mock import MagicMock, call

from plugins import notes


def test_note_add(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    res = notes.note(text="add foo", db=db, event=event)
    assert res is None

    assert event.mock_calls == [call.notice("Note added!")]
    assert mock_db.get_data(notes.table) == [
        (1, "test", "bar", "foo", None, False, datetime.datetime.now())
    ]


def test_note_add_multiple(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    res = notes.note(text="add foo", db=db, event=event)
    res1 = notes.note(text="add foo1", db=db, event=event)
    assert res is None
    assert res1 is None

    assert event.mock_calls == [
        call.notice("Note added!"),
        call.notice("Note added!"),
    ]
    assert mock_db.get_data(notes.table) == [
        (1, "test", "bar", "foo", None, False, datetime.datetime.now()),
        (2, "test", "bar", "foo1", None, False, datetime.datetime.now()),
    ]


def test_note_del(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    res = notes.note(text="del 1", db=db, event=event)
    assert res is None


def test_note_del_no_text(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    res = notes.note(text="del", db=db, event=event)
    assert res == "No note ID provided!"

    assert event.mock_calls == []
    assert mock_db.get_data(notes.table) == [
        (
            1,
            event.conn.name,
            nick,
            "testing",
            None,
            False,
            datetime.datetime.now(),
        )
    ]


def test_note_get(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    res = notes.note(text="get 1", db=db, event=event)
    assert res is None

    assert event.mock_calls == [
        call.notice("\x02Note #1:\x02 testing - \x0222 Aug, 2019\x02")
    ]
    assert mock_db.get_data(notes.table) == [
        (
            1,
            event.conn.name,
            nick,
            "testing",
            None,
            False,
            datetime.datetime.now(),
        )
    ]


def test_note_get_no_id(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    res = notes.note(text="get", db=db, event=event)
    assert res is None

    assert event.mock_calls == [call.notice("No note ID provided!")]
    assert mock_db.get_data(notes.table) == [
        (
            1,
            event.conn.name,
            nick,
            "testing",
            None,
            False,
            datetime.datetime.now(),
        )
    ]


def test_note_get_bad_id(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    res = notes.note(text="2", db=db, event=event)
    assert res is None

    assert event.mock_calls == [call.notice("2 is not a valid note ID.")]


def test_note_show_no_id(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    res = notes.note(text="show", db=db, event=event)
    assert res is None

    assert event.mock_calls == [call.notice("No note ID provided!")]


def test_note_show_bad_id(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    res = notes.note(text="show 2", db=db, event=event)
    assert res is None

    assert event.mock_calls == [call.notice("2 is not a valid note ID.")]


def test_note_share(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    res = notes.note(text="share 1", db=db, event=event)
    assert res == "\x02Note #1:\x02 testing - \x0222 Aug, 2019\x02"

    assert event.mock_calls == []


def test_note_bad_cmd(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    res = notes.note(text="foo", db=db, event=event)

    assert res is None

    assert event.mock_calls == [call.notice("Unknown command: foo")]
    assert mock_db.get_data(notes.table) == []


def test_note_list(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    notes.add_note(db, event.conn.name, nick, "testing1")
    notes.add_note(db, event.conn.name, nick, "testing2")
    notes.delete_note(db, event.conn.name, nick, 2)
    res = notes.note(text="list", db=db, event=event)
    assert res is None

    assert event.mock_calls == [
        call.notice("All notes for bar:"),
        call.notice("\x02Note #1:\x02 testing - \x0222 Aug, 2019\x02"),
        call.notice("\x02Note #3:\x02 testing2 - \x0222 Aug, 2019\x02"),
    ]


def test_note_listall(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    notes.add_note(db, event.conn.name, nick, "testing1")
    notes.add_note(db, event.conn.name, nick, "testing2")
    notes.delete_note(db, event.conn.name, nick, 2)
    res = notes.note(text="listall", db=db, event=event)
    assert res is None

    assert event.mock_calls == [
        call.notice("All notes for bar:"),
        call.notice("\x02Note #1:\x02 testing - \x0222 Aug, 2019\x02"),
        call.notice("\x02Note #2:\x02 testing1 - \x0222 Aug, 2019\x02"),
        call.notice("\x02Note #3:\x02 testing2 - \x0222 Aug, 2019\x02"),
    ]


def test_note_list_no_notes(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    res = notes.note(text="list", db=db, event=event)
    assert res is None

    assert event.mock_calls == [call.notice("You have no notes.")]


def test_note_listall_no_notes(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    res = notes.note(text="listall", db=db, event=event)
    assert res is None

    assert event.mock_calls == [call.notice("You have no notes.")]


def test_note_clear(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    nick = "bar"
    notes.add_note(db, event.conn.name, nick, "testing")
    notes.add_note(db, event.conn.name, nick, "testing1")
    res = notes.note(text="clear", db=db, event=event)

    assert res is None

    assert event.mock_calls == [call.notice("All notes deleted!")]
    assert mock_db.get_data(notes.table) == [
        (
            1,
            event.conn.name,
            nick,
            "testing",
            None,
            True,
            datetime.datetime.now(),
        ),
        (
            2,
            event.conn.name,
            nick,
            "testing1",
            None,
            True,
            datetime.datetime.now(),
        ),
    ]


def test_note_del_no_note(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    res = notes.note(text="del 1", db=db, event=event)
    assert res is None

    assert event.mock_calls == [call.notice("#1 is not a valid note ID.")]
    assert mock_db.get_data(notes.table) == []


def test_note_add_no_text(mock_db, freeze_time):
    db = mock_db.session()
    notes.table.create(bind=mock_db.engine)
    event = MagicMock(nick="bar")
    event.conn.name = "test"
    res = notes.note(text="add", db=db, event=event)
    assert res == "No text provided!"
    assert event.mock_calls == []
    assert mock_db.get_data(notes.table) == []
