import random
from datetime import timedelta
from pathlib import Path

from cloudbot.util import database
from plugins import hookup, seen
from tests.util.mock_db import MockDB


def test_load_data(mock_bot_factory):
    bot = mock_bot_factory(
        base_dir=Path(__file__).parent.parent.parent.resolve()
    )
    hookup.load_data(bot)
    assert hookup.hookups


def test_hookup_no_seen(mock_db: MockDB):
    db = mock_db.session()
    res = hookup.hookup(db, "#chan")
    assert res is None


def test_hookup_no_data(mock_db: MockDB):
    database.metadata._add_table(seen.table.name, seen.table.schema, seen.table)
    seen.table.create(mock_db.engine)
    db = mock_db.session()
    res = hookup.hookup(db, "#chan")
    assert res == "something went wrong"


def test_hookup_one_user(mock_db: MockDB, freeze_time):
    database.metadata._add_table(seen.table.name, seen.table.schema, seen.table)
    seen.table.create(mock_db.engine)

    mock_db.load_data(
        seen.table,
        [
            {
                "name": "testnick",
                "time": (
                    freeze_time.time_to_freeze - timedelta(hours=1)
                ).timestamp(),
                "quote": "foo bar baz",
                "chan": "#chan",
                "host": "user@host",
            },
        ],
    )

    db = mock_db.session()
    res = hookup.hookup(db, "#chan")
    assert res == "something went wrong"


def test_hookup_basic(mock_db: MockDB, freeze_time):
    hookup.hookups = {
        "templates": [
            "{user1} : {user2}",
        ],
        "parts": {},
    }

    database.metadata._add_table(seen.table.name, seen.table.schema, seen.table)
    seen.table.create(mock_db.engine)
    mock_db.load_data(
        seen.table,
        [
            {
                "name": "testnick",
                "time": (
                    freeze_time.time_to_freeze - timedelta(hours=2)
                ).timestamp(),
                "quote": "foo bar baz",
                "chan": "#chan",
                "host": "user@host",
            },
            {
                "name": "testnick2",
                "time": (
                    freeze_time.time_to_freeze - timedelta(hours=1)
                ).timestamp(),
                "quote": "foo bar baz",
                "chan": "#chan",
                "host": "user@host",
            },
        ],
    )

    db = mock_db.session()
    random.seed(1)
    res = hookup.hookup(db, "#chan")
    assert res == "testnick2 : testnick"


def test_hookup_active_time(mock_db: MockDB, freeze_time):
    database.metadata._add_table(seen.table.name, seen.table.schema, seen.table)
    seen.table.create(mock_db.engine)
    mock_db.load_data(
        seen.table,
        [
            {
                "name": "testnick",
                "time": (
                    freeze_time.time_to_freeze - timedelta(weeks=1)
                ).timestamp(),
                "quote": "foo bar baz",
                "chan": "#chan",
                "host": "user@host",
            },
            {
                "name": "testnick2",
                "time": (
                    freeze_time.time_to_freeze - timedelta(hours=1)
                ).timestamp(),
                "quote": "foo bar baz",
                "chan": "#chan",
                "host": "user@host",
            },
        ],
    )

    db = mock_db.session()
    res = hookup.hookup(db, "#chan")
    assert res == "something went wrong"
