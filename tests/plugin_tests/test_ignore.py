from unittest.mock import MagicMock

import pytest

from plugins.core import ignore


class MockConn:
    def __init__(self, name):
        self.name = name


def setup_db(mock_db):
    ignore.table.create(mock_db.engine, checkfirst=True)

    sess = mock_db.session()

    sess.execute(ignore.table.delete())

    ignore.load_cache(sess)


def test_ignore(mock_db, patch_paste):
    setup_db(mock_db)

    sess = mock_db.session()

    conn = MockConn("testconn")

    ignore.add_ignore(sess, conn.name, "#chan", "*!*@host")
    ignore.add_ignore(sess, conn.name, "#chan", "*!*@host")

    ignore.add_ignore(sess, conn.name, "*", "*!*@evil.host")

    assert ignore.is_ignored(conn.name, "#chan", "nick!user@host")
    assert ignore.is_ignored(conn.name, "#a_chan", "evil!user@evil.host")

    assert not ignore.is_ignored(conn.name, "#chan", "nick!user@otherhost")

    assert not ignore.is_ignored(conn.name, "#otherchan", "nick!user@host")

    assert not ignore.is_ignored("otherconn", "#chan", "nick!user@host")

    ignore.listignores(sess, conn, "#chan")

    patch_paste.assert_called_with("*!*@host\n")

    ignore.list_all_ignores(sess, conn, "")

    patch_paste.assert_called_with(
        "Ignores for #chan:\n- *!*@host\n\nIgnores for *:\n- *!*@evil.host\n\n"
    )

    ignore.list_all_ignores(sess, conn, "#chan")

    patch_paste.assert_called_with("Ignores for #chan:\n- *!*@host\n\n")

    ignore.list_global_ignores(sess, conn)

    patch_paste.assert_called_with("*!*@evil.host\n")


def test_remove_ignore(mock_db):
    setup_db(mock_db)

    sess = mock_db.session()

    ignore.add_ignore(sess, "testconn", "#chan", "*!*@host")

    assert ignore.is_ignored("testconn", "#chan", "nick!user@host")

    assert ignore.remove_ignore(sess, "testconn", "#chan", "*!*@host")

    assert not ignore.remove_ignore(sess, "testconn", "#chan", "*!*@host")

    assert not ignore.is_ignored("testconn", "#chan", "nick!user@host")


def test_ignore_case(mock_db):
    setup_db(mock_db)

    sess = mock_db.session()

    ignore.add_ignore(sess, "aTestConn", "#AChan", "*!*@OtherHost")

    assert ignore.is_ignored("atestconn", "#achan", "nick!user@otherhost")

    assert ignore.is_ignored("atestcOnn", "#acHan", "nICk!uSer@otherHost")

    assert ignore.remove_ignore(sess, "atestconn", "#achan", "*!*@OTherHost")

    assert mock_db.get_data(ignore.table) == []


@pytest.mark.asyncio
async def test_ignore_sieve(mock_db, event_loop):
    setup_db(mock_db)

    sess = mock_db.session()

    ignore.add_ignore(sess, "testconn", "#chan", "*!*@host")

    _hook = MagicMock()
    bot = MagicMock()
    event = MagicMock()

    _hook.type = "irc_raw"

    assert (await ignore.ignore_sieve(bot, event, _hook)) is event

    _hook.type = "command"
    event.triggered_command = "unignore"

    assert (await ignore.ignore_sieve(bot, event, _hook)) is event

    event.triggered_command = "somecommand"

    event.mask = None

    assert (await ignore.ignore_sieve(bot, event, _hook)) is event

    event.conn.name = "testconn"
    event.chan = "#chan"
    event.mask = "nick!user@host"

    assert (await ignore.ignore_sieve(bot, event, _hook)) is None

    event.conn.name = "testconn1"

    assert (await ignore.ignore_sieve(bot, event, _hook)) is event


def test_get_user():
    conn = MagicMock()

    conn.memory = {}

    assert ignore.get_user(conn, "nick") == "nick!*@*"
    assert ignore.get_user(conn, "nick!user@host") == "nick!user@host"

    conn.memory["users"] = {
        "nick": {"nick": "nick", "user": "user", "host": "host"}
    }

    assert ignore.get_user(conn, "nick") == "*!*@host"


def test_ignore_command(mock_db):
    setup_db(mock_db)

    sess = mock_db.session()

    conn = MagicMock()

    conn.name = "testconn"
    conn.memory = {}

    event = MagicMock()

    ignore.ignore(
        "*!*@host", sess, "#chan", conn, event.notice, event.admin_log, "opnick"
    )

    event.admin_log.assert_called_with(
        "opnick used IGNORE to make me ignore *!*@host in #chan"
    )
    event.notice.assert_called_with("*!*@host has been ignored in #chan.")
    assert ignore.is_ignored("testconn", "#chan", "nick!user@host")

    event.reset_mock()

    ignore.global_ignore(
        "*!*@host", sess, conn, event.notice, "opnick", event.admin_log
    )

    event.admin_log.assert_called_with(
        "opnick used GLOBAL_IGNORE to make me ignore *!*@host everywhere"
    )
    event.notice.assert_called_with("*!*@host has been globally ignored.")
    assert ignore.is_ignored("testconn", "#otherchan", "nick!user@host")

    event.reset_mock()

    ignore.ignore(
        "*!*@host", sess, "#chan", conn, event.notice, event.admin_log, "opnick"
    )

    event.notice.assert_called_with("*!*@host is already ignored in #chan.")

    event.reset_mock()

    ignore.global_ignore(
        "*!*@host", sess, conn, event.notice, "opnick", event.admin_log
    )

    event.notice.assert_called_with("*!*@host is already globally ignored.")


def test_unignore_command(mock_db):
    setup_db(mock_db)

    sess = mock_db.session()

    conn = MagicMock()

    conn.name = "testconn"
    conn.memory = {}

    event = MagicMock()

    ignore.unignore(
        "*!*@host", sess, "#chan", conn, event.notice, "opnick", event.admin_log
    )

    event.notice.assert_called_with("*!*@host is not ignored in #chan.")

    ignore.add_ignore(sess, "testconn", "#chan", "*!*@host")

    event.reset_mock()

    ignore.unignore(
        "*!*@host", sess, "#chan", conn, event.notice, "opnick", event.admin_log
    )

    event.notice.assert_called_with("*!*@host has been un-ignored in #chan.")
    event.admin_log.assert_called_with(
        "opnick used UNIGNORE to make me stop ignoring *!*@host in #chan"
    )

    assert not ignore.is_ignored("testconn", "#chan", "nick!user@host")

    event.reset_mock()

    ignore.global_unignore(
        "*!*@host", sess, conn, event.notice, "opnick", event.admin_log
    )

    event.notice.assert_called_with("*!*@host is not globally ignored.")

    ignore.add_ignore(sess, "testconn", "*", "*!*@host")

    event.reset_mock()

    ignore.global_unignore(
        "*!*@host", sess, conn, event.notice, "opnick", event.admin_log
    )

    event.notice.assert_called_with("*!*@host has been globally un-ignored.")
    event.admin_log.assert_called_with(
        "opnick used GLOBAL_UNIGNORE to make me stop ignoring *!*@host everywhere"
    )

    assert not ignore.is_ignored("testconn", "#chan", "nick!user@host")

    event.reset_mock()
