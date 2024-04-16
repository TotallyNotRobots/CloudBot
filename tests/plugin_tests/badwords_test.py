from unittest.mock import MagicMock, call

import pytest

from cloudbot.clients.irc import IrcClient
from plugins import badwords
from tests.util.mock_db import MockDB


@pytest.fixture()
def clear_bad_words():
    badwords.badcache.clear()
    yield
    badwords.badcache.clear()


pytestmark = pytest.mark.usefixtures("clear_bad_words")


def test_add_bad(mock_db: MockDB):
    badwords.table.create(mock_db.engine)
    with mock_db.session() as session:
        res = badwords.add_bad("foo #bar", "testnick", session)
        assert res == "Current badwords: foo"
        assert mock_db.get_data(badwords.table) == [
            ("foo", "testnick", "#bar"),
        ]


def test_del_bad(mock_db: MockDB):
    badwords.table.create(mock_db.engine)
    with mock_db.session() as session:
        mock_db.load_data(
            badwords.table,
            [
                {"word": "foo", "nick": "testnick", "chan": "#bar"},
            ],
        )
        badwords.load_bad(session)
        res = badwords.del_bad("foo #bar", session)
        assert res == "Removing foo new bad word list for #bar is: foo"
        assert mock_db.get_data(badwords.table) == []


def test_check_badwords(mock_db: MockDB):
    badwords.table.create(mock_db.engine)
    with mock_db.session() as session:
        mock_db.load_data(
            badwords.table,
            [
                {"word": "foo", "nick": "testnick", "chan": "#bar"},
            ],
        )

        badwords.load_bad(session)
        assert badwords.matcher.regex
        assert badwords.badcache["#bar"] == ["foo"]
        conn = MagicMock()
        # conn.configure_mock()
        conn.mock_add_spec(spec=IrcClient, spec_set=True)
        message = MagicMock()
        res = badwords.check_badwords(conn, message, "#bar", "foo", "user123")
        assert res is None
        assert message.mock_calls == [
            call("user123, congratulations you've won!")
        ]
        assert conn.mock_calls == [
            call.cmd(
                "KICK",
                "#bar",
                "user123",
                "that fucking word is so damn offensive",
            )
        ]


def test_check_badwords_wrong_channel(mock_db: MockDB):
    badwords.table.create(mock_db.engine)
    with mock_db.session() as session:
        mock_db.load_data(
            badwords.table,
            [
                {"word": "foo", "nick": "testnick", "chan": "#bar"},
            ],
        )

        badwords.load_bad(session)
        assert badwords.matcher.regex
        assert badwords.badcache["#bar"] == ["foo"]
        conn = MagicMock()
        # conn.configure_mock()
        conn.mock_add_spec(spec=IrcClient, spec_set=True)
        message = MagicMock()
        res = badwords.check_badwords(conn, message, "#bar2", "foo", "user123")
        assert res is None
        assert message.mock_calls == []
        assert conn.mock_calls == []


def test_check_badwords_no_match(mock_db: MockDB):
    badwords.table.create(mock_db.engine)
    with mock_db.session() as session:
        mock_db.load_data(
            badwords.table,
            [
                {"word": "foo", "nick": "testnick", "chan": "#bar"},
            ],
        )

        badwords.load_bad(session)
        assert badwords.matcher.regex
        assert badwords.badcache["#bar"] == ["foo"]
        conn = MagicMock()
        # conn.configure_mock()
        conn.mock_add_spec(spec=IrcClient, spec_set=True)
        message = MagicMock()
        res = badwords.check_badwords(
            conn, message, "#bar", "foobar", "user123"
        )
        assert res is None
        assert message.mock_calls == []
        assert conn.mock_calls == []
