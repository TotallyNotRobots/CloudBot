import datetime as dt
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, call, patch

import pytest
from irclib.parser import Prefix

from plugins import tell
from tests.util.mock_conn import MockClient

if TYPE_CHECKING:
    import sqlalchemy as sa


def init_tables(mock_db) -> None:
    db_engine = mock_db.engine
    cast("sa.Table", tell.TellMessage.__table__).create(db_engine)
    tell.disable_table.create(db_engine)
    tell.ignore_table.create(db_engine)
    session = mock_db.session()
    tell.load_cache(session)
    tell.load_disabled(session)
    tell.load_ignores(session)


def test_tellcmd(mock_db) -> None:
    init_tables(mock_db)
    session = mock_db.session()

    mock_event = MagicMock()
    mock_event.is_nick_valid.return_value = True
    mock_conn = MagicMock()
    mock_conn.nick = "BotNick"
    mock_conn.name = "MockConn"
    sender = Prefix("TestUser", "user", "example.com")

    def _test(text, output) -> None:
        tell.tell_cmd(
            text, sender.nick, session, mock_conn, sender.mask, mock_event
        )

        mock_event.notice.assert_called_with(output)

        mock_event.reset_mock()

    tell.tell_cmd(
        "OtherUser", sender.nick, session, mock_conn, sender.mask, mock_event
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
    _test(f"{sender.nick} some message", "Have you looked in a mirror lately?")

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10

    with patch("plugins.tell.can_send_to_user") as mocked:
        mocked.return_value = False
        _test("OtherUser some message", "You may not send a tell to that user.")

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10


@pytest.mark.asyncio
async def test_showtells(mock_db, freeze_time, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=bot)
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
            dt.datetime(2019, 8, 22, 13, 14, 36),
            None,
        )
    ]

    freeze_time.tick(dt.timedelta(minutes=1))
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
            dt.datetime(2019, 8, 22, 13, 14, 36),
            None,
        )
    ]


@pytest.mark.asyncio
async def test_showtells_no_tells(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=bot)
    nick = "other"
    event = MagicMock()
    res = tell.showtells(nick, event.notice, db, conn)
    assert res is None
    assert event.mock_calls == [call.notice("You have no pending messages.")]


def test_tellinput_showtells(mock_db, freeze_time, mock_bot) -> None:
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=mock_bot)
    nick = "other"
    event = MagicMock()
    content = ". showtells 1 2 3"
    res = tell.tellinput(conn, db, nick, event.notice, content)
    assert res is None
    assert event.mock_calls == []


def test_tellinput_no_tells(mock_db, freeze_time, mock_bot) -> None:
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=mock_bot)
    nick = "other"
    event = MagicMock()
    content = "aa"
    tell.tell_cache.append((conn.name, "someuser"))
    res = tell.tellinput(conn, db, nick, event.notice, content)
    assert res is None
    assert event.mock_calls == []


def test_tellinput_bad_cache(mock_db, freeze_time, mock_bot) -> None:
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=mock_bot)
    nick = "other"
    event = MagicMock()
    content = "aa"
    tell.tell_cache.append((conn.name, nick.lower()))
    res = tell.tellinput(conn, db, nick, event.notice, content)
    assert res is None
    assert event.mock_calls == []


def test_tellinput(mock_db, freeze_time, mock_bot) -> None:
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=mock_bot)
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


def test_read_tell_spam(mock_db, freeze_time, mock_bot) -> None:
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=mock_bot)
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
            dt.datetime(2019, 8, 22, 13, 14, 36),
            None,
        ),
        (
            2,
            "testconn",
            sender,
            nick,
            message,
            False,
            dt.datetime(2019, 8, 22, 13, 14, 37),
            None,
        ),
        (
            3,
            "testconn",
            sender,
            nick,
            message,
            False,
            dt.datetime(2019, 8, 22, 13, 14, 38),
            None,
        ),
        (
            4,
            "testconn",
            sender,
            nick,
            message2,
            False,
            dt.datetime(2019, 8, 22, 13, 14, 39),
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


def test_tellinput_multiple(mock_db, freeze_time, mock_bot) -> None:
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=mock_bot)
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
            dt.datetime(2019, 8, 22, 13, 14, 36),
            dt.datetime(2019, 8, 22, 13, 14, 36),
        ),
        (
            2,
            "testconn",
            "foo",
            "other",
            "test",
            False,
            dt.datetime(2019, 8, 22, 13, 14, 36),
            None,
        ),
        (
            3,
            "testconn",
            "foo",
            "other",
            "z",
            False,
            dt.datetime(2019, 8, 22, 13, 14, 36),
            None,
        ),
    ]


@pytest.mark.asyncio
async def test_can_send_to_user(mock_db, freeze_time, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=bot)
    target = "otheruser"
    sender_mask = "foo!bar@baz"
    tell.add_ignore(db, conn, target, "foo")
    assert tell.can_send_to_user(conn, sender_mask, target) is True


@pytest.mark.asyncio
async def test_can_send_to_user_disabled(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=bot)
    target = "otheruser"
    sender_mask = "foo!bar@baz"
    assert tell.can_send_to_user(conn, sender_mask, target) is True

    tell.add_disable(db, conn, target, target)
    assert tell.can_send_to_user(conn, sender_mask, target) is False


@pytest.mark.asyncio
async def test_can_send_to_user_ignored(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    init_tables(mock_db)
    db = mock_db.session()
    conn = MockClient(bot=bot)
    target = "otheruser"
    sender_mask = "foo!bar@baz"
    assert tell.can_send_to_user(conn, sender_mask, target) is True

    tell.add_ignore(db, conn, target, sender_mask)
    assert tell.can_send_to_user(conn, sender_mask, target) is False


def test_load_disabled(mock_db, freeze_time) -> None:
    init_tables(mock_db)
    session = mock_db.session()

    mock_db.add_row(
        tell.disable_table,
        conn="foo",
        target="bar",
        setter="baz",
        set_at=dt.datetime.now(),
    )

    tell.load_disabled(session)

    assert tell.disable_cache == {"foo": {"bar"}}


@pytest.mark.asyncio
async def test_add_disabled(mock_db, freeze_time, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    db_engine = mock_db.engine
    tell.disable_table.create(db_engine)
    session = mock_db.session()
    conn = MockClient(bot=bot)
    now = dt.datetime.now()
    tell.add_disable(session, conn, "foo", "bar", now=now)

    assert tell.disable_cache == {"testconn": {"bar"}}
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "bar", "foo", dt.datetime(2019, 8, 22, 13, 14, 36))
    ]


@pytest.mark.asyncio
async def test_del_disabled(mock_db, freeze_time, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    db_engine = mock_db.engine
    tell.disable_table.create(db_engine)
    session = mock_db.session()
    conn = MockClient(bot=bot)
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target="bar",
        setter="baz",
        set_at=dt.datetime.now(),
    )

    tell.load_disabled(session)

    tell.del_disable(session, conn, "bar")

    assert mock_db.get_data(tell.disable_table) == []
    assert tell.disable_cache == {}


def test_load_ignored(mock_db, freeze_time) -> None:
    db_engine = mock_db.engine
    tell.ignore_table.create(db_engine)
    session = mock_db.session()

    mock_db.add_row(
        tell.ignore_table,
        conn="foo",
        nick="bar",
        mask="baz",
        set_at=dt.datetime.now(),
    )

    tell.load_ignores(session)

    assert tell.ignore_cache == {"foo": {"bar": ["baz"]}}


@pytest.mark.asyncio
async def test_tell_disable(mock_db, freeze_time, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    db = mock_db.session()
    text = ""
    nick = "foo"
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are now disabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "foo", "foo", dt.datetime(2019, 8, 22, 13, 14, 36))
    ]


@pytest.mark.asyncio
async def test_tell_disable_self(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    db = mock_db.session()
    nick = "foo"
    text = nick
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are now disabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "foo", "foo", dt.datetime(2019, 8, 22, 13, 14, 36))
    ]


@pytest.mark.asyncio
async def test_tell_disable_no_perms(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = False
    conn = MockClient(bot=bot)
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


@pytest.mark.asyncio
async def test_tell_disable_other(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    db = mock_db.session()
    nick = "foo"
    text = "other"
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are now disabled for 'other'."
    assert event.mock_calls == [call.has_permission("botcontrol")]
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "other", "foo", dt.datetime(2019, 8, 22, 13, 14, 36))
    ]


@pytest.mark.asyncio
async def test_tell_disable_already_disabled(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    nick = "foo"
    text = ""
    conn = MockClient(bot=bot)
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=nick,
        setter=nick,
        set_at=dt.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are already disabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "foo", "foo", dt.datetime(2019, 8, 22, 13, 14, 36))
    ]


@pytest.mark.asyncio
async def test_tell_disable_already_disabled_other(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    nick = "foo"
    text = "other"
    conn = MockClient(bot=bot)
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=text,
        setter=nick,
        set_at=dt.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_disable(conn, db, text, nick, event)
    assert res == "Tells are already disabled for 'other'."
    assert event.mock_calls == [call.has_permission("botcontrol")]
    assert mock_db.get_data(tell.disable_table) == [
        ("testconn", "other", "foo", dt.datetime(2019, 8, 22, 13, 14, 36))
    ]


@pytest.mark.asyncio
async def test_tell_enable(mock_db, freeze_time, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    conn = MockClient(bot=bot)
    text = ""
    nick = "foo"
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=nick,
        setter=nick,
        set_at=dt.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are now enabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == []


@pytest.mark.asyncio
async def test_tell_enable_self(mock_db, freeze_time, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    db = mock_db.session()
    nick = "foo"
    text = nick
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=nick,
        setter=nick,
        set_at=dt.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are now enabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == []


@pytest.mark.asyncio
async def test_tell_enable_no_perms(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = False
    conn = MockClient(bot=bot)
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


@pytest.mark.asyncio
async def test_tell_enable_other(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    db = mock_db.session()
    nick = "foo"
    text = "other"
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=text,
        setter=nick,
        set_at=dt.datetime.now(),
    )
    tell.load_disabled(mock_db.session())
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are now enabled for 'other'."
    assert event.mock_calls == [call.has_permission("botcontrol")]
    assert mock_db.get_data(tell.disable_table) == []


@pytest.mark.asyncio
async def test_tell_enable_already_enabled(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    nick = "foo"
    text = ""
    conn = MockClient(bot=bot)
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are already enabled for you."
    assert event.mock_calls == []
    assert mock_db.get_data(tell.disable_table) == []


@pytest.mark.asyncio
async def test_tell_enable_already_enabled_other(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    nick = "foo"
    text = "other"
    conn = MockClient(bot=bot)
    event.has_permission.return_value = True
    db = mock_db.session()
    res = tell.tell_enable(conn, db, text, event, nick)
    assert res == "Tells are already enabled for 'other'."
    assert event.mock_calls == [call.has_permission("botcontrol")]
    assert mock_db.get_data(tell.disable_table) == []


@pytest.mark.asyncio
async def test_tell_list_disabled(
    mock_db, freeze_time, mock_bot_factory, patch_paste
) -> None:
    bot = mock_bot_factory(db=mock_db)
    patch_paste.return_value = "Pasted."
    event = MagicMock()
    tell.disable_cache.clear()
    tell.disable_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    db = mock_db.session()
    nick = "foo"
    text = "other"
    mock_db.add_row(
        tell.disable_table,
        conn=conn.name.lower(),
        target=text,
        setter=nick,
        set_at=dt.datetime.now(),
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


@pytest.mark.asyncio
async def test_tell_ignore(mock_db, freeze_time, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
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
        ("testconn", dt.datetime(2019, 8, 22, 13, 14, 36), "foo", "other")
    ]


@pytest.mark.asyncio
async def test_tell_ignore_existing(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    nick = "foo"
    text = "other"
    db = mock_db.session()
    tell.add_ignore(db, conn, nick, text, now=dt.datetime.now())
    res = tell.tell_ignore(db, conn, nick, text, event.notice)
    assert res is None
    assert event.mock_calls == [
        call.notice("You are already ignoring tells from 'other'")
    ]
    assert mock_db.get_data(tell.ignore_table) == [
        ("testconn", dt.datetime(2019, 8, 22, 13, 14, 36), "foo", "other")
    ]


@pytest.mark.asyncio
async def test_tell_unignore_not_Set(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
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


@pytest.mark.asyncio
async def test_tell_unignore(mock_db, freeze_time, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    nick = "foo"
    text = "other"
    db = mock_db.session()
    mock_db.add_row(
        tell.ignore_table,
        conn=conn.name.lower(),
        nick=nick,
        mask=text,
        set_at=dt.datetime.now(),
    )
    tell.load_ignores(mock_db.session())
    res = tell.tell_unignore(db, conn, nick, text, event.notice)
    assert res is None
    assert event.mock_calls == [call.notice("'other' has been unignored")]
    assert mock_db.get_data(tell.ignore_table) == []


@pytest.mark.asyncio
async def test_tell_list_ignores(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    nick = "foo"
    text = "other"
    mock_db.add_row(
        tell.ignore_table,
        conn=conn.name.lower(),
        nick=nick,
        mask=text,
        set_at=dt.datetime.now(),
    )
    tell.load_ignores(mock_db.session())
    res = tell.list_tell_ignores(conn, nick)
    assert res == "You are ignoring tell from: 'other'"
    assert event.mock_calls == []


@pytest.mark.asyncio
async def test_tell_list_ignores_empty(
    mock_db, freeze_time, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    event = MagicMock()
    tell.ignore_cache.clear()
    tell.ignore_table.create(mock_db.engine)
    event.has_permission.return_value = True
    conn = MockClient(bot=bot)
    nick = "foo"
    tell.load_ignores(mock_db.session())
    res = tell.list_tell_ignores(conn, nick)
    assert res == "You are not ignoring tells from any users"
    assert event.mock_calls == []
