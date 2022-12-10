import datetime
from unittest.mock import MagicMock, call, patch

import sqlalchemy as sa
from irclib.parser import Prefix

from cloudbot.util import database
from plugins import tell
from tests.util.mock_conn import MockConn


def init_tables(mock_db):
    db_engine = mock_db.engine
    tell.TellMessage.__table__.create(db_engine)
    tell.disable_table.create(db_engine)
    tell.ignore_table.create(db_engine)
    session = mock_db.session()
    tell.load_cache(session)
    tell.load_disabled(session)
    tell.load_ignores(session)


def test_migrate_db(mock_db, freeze_time):
    init_tables(mock_db)
    session = mock_db.session()

    tbl = sa.Table(
        "tells",
        database.metadata,
        sa.Column("connection", sa.String),
        sa.Column("sender", sa.String),
        sa.Column("target", sa.String),
        sa.Column("message", sa.String),
        sa.Column("is_read", sa.Boolean),
        sa.Column("time_sent", sa.DateTime),
        sa.Column("time_read", sa.DateTime),
    )

    tbl.create(mock_db.engine)
    mock_db.add_row(
        tbl,
        connection="conn",
        sender="foo",
        target="bar",
        message="foobar",
        is_read=False,
        time_sent=datetime.datetime.now(),
        time_read=None,
    )

    database.metadata.clear()

    assert mock_db.get_data(tbl) == [
        (
            "conn",
            "foo",
            "bar",
            "foobar",
            False,
            datetime.datetime(2019, 8, 22, 13, 14, 36),
            None,
        )
    ]

    tell.migrate_tables(session)

    assert not sa.inspect(mock_db.engine).has_table(tbl.name)
    assert mock_db.get_data(tell.TellMessage.__table__) == [
        (
            1,
            "conn",
            "foo",
            "bar",
            "foobar",
            False,
            datetime.datetime(2019, 8, 22, 13, 14, 36),
            None,
        )
    ]


def test_tellcmd(mock_db):
    init_tables(mock_db)
    session = mock_db.session()

    mock_event = MagicMock()
    mock_event.is_nick_valid.return_value = True
    mock_conn = MagicMock()
    mock_conn.nick = "BotNick"
    mock_conn.name = "MockConn"
    sender = Prefix("TestUser", "user", "example.com")

    def _test(text, output):
        tell.tell_cmd(
            text,
            sender.nick,
            session,
            mock_conn,
            sender.mask,
            mock_event,
        )

        mock_event.notice.assert_called_with(output)

        mock_event.reset_mock()

    tell.tell_cmd(
        "OtherUser",
        sender.nick,
        session,
        mock_conn,
        sender.mask,
        mock_event,
    )

    mock_event.notice_doc.assert_called_once_with()

    mock_event.reset_mock()

    _test(
        "OtherUser some message",
        "Your message has been saved, and OtherUser will be notified once they are active.",
    )

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 1

    for i in range(9):
        _test(
            "OtherUser some message",
            "Your message has been saved, and OtherUser will be notified once they are active.",
        )

        assert tell.count_unread(session, mock_conn.name, "OtherUser") == 2 + i

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10

    _test(
        "OtherUser some message",
        "Sorry, OtherUser has too many messages queued already.",
    )

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10

    mock_event.is_nick_valid.return_value = False

    _test("OtherUser some message", "Invalid nick 'OtherUser'.")

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10

    mock_event.is_nick_valid.return_value = True
    _test(sender.nick + " some message", "Have you looked in a mirror lately?")

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10

    with patch("plugins.tell.can_send_to_user") as mocked:
        mocked.return_value = False
        _test("OtherUser some message", "You may not send a tell to that user.")

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10


def test_showtells(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    server = conn.name.lower()
    sender = "foo"
    nick = target = "other"
    message = "bar"
    event = MagicMock()
    tell.add_tell(mock_db.session(), server, sender, target, message)

    assert mock_db.get_data(tell.TellMessage.__table__) == [
        (
            1,
            "testconn",
            "foo",
            "other",
            "bar",
            False,
            datetime.datetime(2019, 8, 22, 13, 14, 36),
            None,
        )
    ]

    freeze_time.tick(datetime.timedelta(minutes=1))
    res = tell.showtells(nick, event.notice, db, conn)
    assert res is None
    assert event.mock_calls == [
        call.notice("foo sent you a message 60 seconds ago: bar")
    ]
    assert mock_db.get_data(tell.TellMessage.__table__) == [
        (
            1,
            "testconn",
            "foo",
            "other",
            "bar",
            True,
            datetime.datetime(2019, 8, 22, 13, 14, 36),
            None,
        )
    ]


def test_showtells_no_tells(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    nick = "other"
    event = MagicMock()
    res = tell.showtells(nick, event.notice, db, conn)
    assert res is None
    assert event.mock_calls == [call.notice("You have no pending messages.")]


def test_tellinput_showtells(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    nick = "other"
    event = MagicMock()
    content = ". showtells 1 2 3"
    res = tell.tellinput(conn, db, nick, event.notice, content)
    assert res is None
    assert event.mock_calls == []


def test_tellinput_no_tells(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    nick = "other"
    event = MagicMock()
    content = "aa"
    tell.tell_cache.append((conn.name, "someuser"))
    res = tell.tellinput(conn, db, nick, event.notice, content)
    assert res is None
    assert event.mock_calls == []


def test_tellinput_bad_cache(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    nick = "other"
    event = MagicMock()
    content = "aa"
    tell.tell_cache.append((conn.name, nick.lower()))
    res = tell.tellinput(conn, db, nick, event.notice, content)
    assert res is None
    assert event.mock_calls == []


def test_tellinput(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    sender = "foo"
    nick = "other"
    message = "bar"
    event = MagicMock()
    content = "aa"
    tell.add_tell(db, conn.name.lower(), sender, nick, message)
    res = tell.tellinput(conn, db, nick, event.notice, content)
    assert res is None
    assert event.mock_calls == [
        call.notice("foo sent you a message 0 minutes ago: bar")
    ]


def test_read_tell_spam(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    conn.config["command_prefix"] = "."
    sender = "foo"
    nick = "other"
    message = "bar"
    message2 = "baraa"
    event = MagicMock()
    content = "aa"
    tell.add_tell(db, conn.name.lower(), sender, nick, message)
    freeze_time.tick()
    tell.add_tell(db, conn.name.lower(), sender, nick, message)
    freeze_time.tick()
    tell.add_tell(db, conn.name.lower(), sender, nick, message)
    freeze_time.tick()
    tell.add_tell(db, conn.name.lower(), sender, nick, message2)
    assert mock_db.get_data(tell.TellMessage.__table__) == [
        (
            1,
            "testconn",
            sender,
            nick,
            message,
            False,
            datetime.datetime(2019, 8, 22, 13, 14, 36),
            None,
        ),
        (
            2,
            "testconn",
            sender,
            nick,
            message,
            False,
            datetime.datetime(2019, 8, 22, 13, 14, 37),
            None,
        ),
        (
            3,
            "testconn",
            sender,
            nick,
            message,
            False,
            datetime.datetime(2019, 8, 22, 13, 14, 38),
            None,
        ),
        (
            4,
            "testconn",
            sender,
            nick,
            message2,
            False,
            datetime.datetime(2019, 8, 22, 13, 14, 39),
            None,
        ),
    ]
    res = tell.tellinput(conn, db, nick, event.notice, content)
    assert res is None
    assert event.mock_calls == [
        call.notice(
            "foo sent you a message 3 seconds ago: bar (+3 more, .showtells to view)"
        )
    ]


def test_tellinput_multiple(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    conn.config["command_prefix"] = "."
    sender = "foo"
    nick = "other"
    message = "bar"
    event = MagicMock()
    content = "aa"
    tell.add_tell(db, conn.name.lower(), sender, nick, message)
    tell.add_tell(db, conn.name.lower(), sender, nick, "test")
    tell.add_tell(db, conn.name.lower(), sender, nick, "z")
    res = tell.tellinput(conn, db, nick, event.notice, content)
    assert res is None
    assert event.mock_calls == [
        call.notice(
            "foo sent you a message 0 minutes ago: bar (+2 more, .showtells to view)"
        )
    ]
    assert mock_db.get_data(tell.TellMessage.__table__) == [
        (
            1,
            "testconn",
            "foo",
            "other",
            "bar",
            True,
            datetime.datetime(2019, 8, 22, 13, 14, 36),
            datetime.datetime(2019, 8, 22, 13, 14, 36),
        ),
        (
            2,
            "testconn",
            "foo",
            "other",
            "test",
            False,
            datetime.datetime(2019, 8, 22, 13, 14, 36),
            None,
        ),
        (
            3,
            "testconn",
            "foo",
            "other",
            "z",
            False,
            datetime.datetime(2019, 8, 22, 13, 14, 36),
            None,
        ),
    ]


def test_can_send_to_user(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    target = "otheruser"
    sender_mask = "foo!bar@baz"
    tell.add_ignore(db, conn, target, "foo")
    assert tell.can_send_to_user(conn, sender_mask, target) is True


def test_can_send_to_user_disabled(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    target = "otheruser"
    sender_mask = "foo!bar@baz"
    assert tell.can_send_to_user(conn, sender_mask, target) is True

    tell.add_disable(db, conn, target, target)
    assert tell.can_send_to_user(conn, sender_mask, target) is False


def test_can_send_to_user_ignored(mock_db, freeze_time):
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockConn()
    target = "otheruser"
    sender_mask = "foo!bar@baz"
    assert tell.can_send_to_user(conn, sender_mask, target) is True

    tell.add_ignore(db, conn, target, sender_mask)
    assert tell.can_send_to_user(conn, sender_mask, target) is False


def test_load_disabled(mock_db, freeze_time):
    init_tables(mock_db)
    session = mock_db.session()

    mock_db.add_row(
        tell.disable_table,
        conn="foo",
        target="bar",
        setter="baz",
        set_at=datetime.datetime.now(),
    )

    tell.load_disabled(session)

    assert tell.disable_cache == {"foo": {"bar"}}


def test_add_disabled(mock_db, freeze_time):
    db_engine = mock_db.engine
    tell.disable_table.create(db_engine)
    session = mock_db.session()
    conn = MockConn()
    now = datetime.datetime.now()
    tell.add_disable(session, conn, "foo", "bar", now=now)

    assert tell.disable_cache == {"testconn": {"bar"}}
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "bar", "foo", datetime.datetime(2019, 8, 22, 13, 14, 36))
    ]


def test_del_disabled(mock_db, freeze_time):
    db_engine = mock_db.engine
    tell.disable_table.create(db_engine)
    session = mock_db.session()
    conn = MockConn()
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target="bar",
        setter="baz",
        set_at=datetime.datetime.now(),
    )

    tell.load_disabled(session)

    tell.del_disable(session, conn, "bar")

    assert mock_db.get_data(tell.disable_table) == []
    assert tell.disable_cache == {}


def test_load_ignored(mock_db, freeze_time):
    db_engine = mock_db.engine
    tell.ignore_table.create(db_engine)
    session = mock_db.session()

    mock_db.add_row(
        tell.ignore_table,
        conn="foo",
        nick="bar",
        mask="baz",
        set_at=datetime.datetime.now(),
    )

    tell.load_ignores(session)

    assert tell.ignore_cache == {"foo": {"bar": ["baz"]}}


def test_tell_disable(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    db = mock_db.session()
    text = ""
    nick = "foo"
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are now disabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "foo", "foo", datetime.datetime(2019, 8, 22, 13, 14, 36))
    ]


def test_tell_disable_self(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    db = mock_db.session()
    nick = "foo"
    text = nick
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are now disabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "foo", "foo", datetime.datetime(2019, 8, 22, 13, 14, 36))
    ]


def test_tell_disable_no_perms(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = False
    conn = MockConn()
    db = mock_db.session()
    nick = "foo"
    text = "other"
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res is None
    assert event.mock_calls == [
        call.has_permission("botcontrol"),
        call.has_permission("ignore"),
        call.notice("Sorry, you are not allowed to use this command."),
    ]
    assert mock_db.get_data(tell.disable_table) == []


def test_tell_disable_other(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    db = mock_db.session()
    nick = "foo"
    text = "other"
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are now disabled for 'other'."
    assert event.mock_calls == [call.has_permission("botcontrol")]
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "other", "foo", datetime.datetime(2019, 8, 22, 13, 14, 36))
    ]


def test_tell_disable_already_disabled(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    nick = "foo"
    text = ""
    conn = MockConn()
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=nick,
        setter=nick,
        set_at=datetime.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are already disabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "foo", "foo", datetime.datetime(2019, 8, 22, 13, 14, 36))
    ]


def test_tell_disable_already_disabled_other(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    nick = "foo"
    text = "other"
    conn = MockConn()
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=text,
        setter=nick,
        set_at=datetime.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are already disabled for 'other'."
    assert event.mock_calls == [call.has_permission("botcontrol")]
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "other", "foo", datetime.datetime(2019, 8, 22, 13, 14, 36))
    ]


def test_tell_enable(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    conn = MockConn()
    text = ""
    nick = "foo"
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=nick,
        setter=nick,
        set_at=datetime.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are now enabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == []


def test_tell_enable_self(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    db = mock_db.session()
    nick = "foo"
    text = nick
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=nick,
        setter=nick,
        set_at=datetime.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are now enabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == []


def test_tell_enable_no_perms(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = False
    conn = MockConn()
    db = mock_db.session()
    nick = "foo"
    text = "other"
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res is None
    assert event.mock_calls == [
        call.has_permission("botcontrol"),
        call.has_permission("ignore"),
        call.notice("Sorry, you are not allowed to use this command."),
    ]
    assert mock_db.get_data(tell.disable_table) == []


def test_tell_enable_other(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    db = mock_db.session()
    nick = "foo"
    text = "other"
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=text,
        setter=nick,
        set_at=datetime.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are now enabled for 'other'."
    assert event.mock_calls == [call.has_permission("botcontrol")]
    assert mock_db.get_data(tell.disable_table) == []


def test_tell_enable_already_enabled(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    nick = "foo"
    text = ""
    conn = MockConn()
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are already enabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == []


def test_tell_enable_already_enabled_other(mock_db, freeze_time):
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    nick = "foo"
    text = "other"
    conn = MockConn()
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are already enabled for 'other'."
    assert event.mock_calls == [call.has_permission("botcontrol")]
    assert mock_db.get_data(tell.disable_table) == []


def test_tell_list_disabled(mock_db, freeze_time, patch_paste):
    patch_paste.return_value = "Pasted."
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    db = mock_db.session()
    nick = "foo"
    text = "other"
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=text,
        setter=nick,
        set_at=datetime.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    res = tell.list_tell_disabled(conn, db)
    assert res == "Pasted."
    assert event.mock_calls == []
    assert patch_paste.mock_calls == [
        call(
            "| Connection | Target | Setter | Set At                   |\n"
            "| ---------- | ------ | ------ | ------------------------ |\n"
            "| testconn   | other  | foo    | Thu Aug 22 13:14:36 2019 |",
            "md",
            "hastebin",
        )
    ]


def test_tell_ignore(mock_db, freeze_time):
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    nick = "foo"
    text = "other"
    db = mock_db.session()
    tell.load_ignores(mock_db.session())
    res = tell.tell_ignore(db, conn, nick, text, event.notice)
    assert res is None
    assert event.mock_calls == [
        call.notice("You are now ignoring tells from 'other'")
    ]
    assert mock_db.get_data(tell.ignore_table) == [
        ("testconn", datetime.datetime(2019, 8, 22, 13, 14, 36), "foo", "other")
    ]


def test_tell_ignore_existing(mock_db, freeze_time):
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    nick = "foo"
    text = "other"
    db = mock_db.session()
    tell.add_ignore(db, conn, nick, text, now=datetime.datetime.now())
    res = tell.tell_ignore(db, conn, nick, text, event.notice)
    assert res is None
    assert event.mock_calls == [
        call.notice("You are already ignoring tells from 'other'")
    ]
    assert mock_db.get_data(tell.ignore_table) == [
        ("testconn", datetime.datetime(2019, 8, 22, 13, 14, 36), "foo", "other")
    ]


def test_tell_unignore_not_Set(mock_db, freeze_time):
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    nick = "foo"
    text = "other"
    db = mock_db.session()
    tell.load_ignores(mock_db.session())
    res = tell.tell_unignore(db, conn, nick, text, event.notice)
    assert res is None
    assert event.mock_calls == [
        call.notice("No ignore matching 'other' exists.")
    ]
    assert mock_db.get_data(tell.ignore_table) == []


def test_tell_unignore(mock_db, freeze_time):
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    nick = "foo"
    text = "other"
    db = mock_db.session()
    mock_db.add_row(
        tell.ignore_table,
        conn=conn.name.lower(),
        nick=nick,
        mask=text,
        set_at=datetime.datetime.now(),
    )
    tell.load_ignores(mock_db.session())
    res = tell.tell_unignore(db, conn, nick, text, event.notice)
    assert res is None
    assert event.mock_calls == [call.notice("'other' has been unignored")]
    assert mock_db.get_data(tell.ignore_table) == []


def test_tell_list_ignores(mock_db, freeze_time):
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    nick = "foo"
    text = "other"
    mock_db.add_row(
        tell.ignore_table,
        conn=conn.name.lower(),
        nick=nick,
        mask=text,
        set_at=datetime.datetime.now(),
    )
    tell.load_ignores(mock_db.session())
    res = tell.list_tell_ignores(conn, nick)
    assert res == "You are ignoring tell from: 'other'"
    assert event.mock_calls == []


def test_tell_list_ignores_empty(mock_db, freeze_time):
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockConn()
    nick = "foo"
    tell.load_ignores(mock_db.session())
    res = tell.list_tell_ignores(conn, nick)
    assert res == "You are not ignoring tells from any users"
    assert event.mock_calls == []
