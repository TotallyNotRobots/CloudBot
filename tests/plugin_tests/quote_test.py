import time
from unittest.mock import MagicMock, call

from sqlalchemy import (
    REAL,
    Column,
    PrimaryKeyConstraint,
    String,
    Table,
    inspect,
)

from cloudbot.util import database
from plugins import quote


def test_migrate(mock_db, freeze_time):
    db = mock_db.session()
    # quote.qtable.create(mock_db.engine)
    old_table = Table(
        "quote",
        database.metadata,
        Column("chan", String(25)),
        Column("nick", String(25)),
        Column("add_nick", String(25)),
        Column("msg", String(500)),
        Column("time", REAL),
        Column("deleted", String(5), default=0),
        PrimaryKeyConstraint("chan", "nick", "time"),
    )

    inspector = inspect(mock_db.engine)
    old_table.create(mock_db.engine)
    mock_db.load_data(
        old_table,
        [
            {
                "chan": "#chan",
                "nick": "nick",
                "add_nick": "other",
                "msg": "foobar",
                "time": 12345,
            },
        ],
    )
    database.metadata.remove(old_table)
    logger = MagicMock()
    quote.migrate_table(db, logger)
    assert not inspector.has_table(old_table.name)
    assert mock_db.get_data(quote.qtable) == [
        ("#chan", "nick", "other", "foobar", 12345.0, False),
    ]
    assert logger.mock_calls == [
        call.info("Migrating quotes table"),
        call.info("Migrated all quotes"),
    ]


def test_migrate_no_old_table(mock_db, freeze_time):
    db = mock_db.session()
    # quote.qtable.create(mock_db.engine)
    old_table = Table(
        "quote",
        database.metadata,
        Column("chan", String(25)),
        Column("nick", String(25)),
        Column("add_nick", String(25)),
        Column("msg", String(500)),
        Column("time", REAL),
        Column("deleted", String(5), default=0),
        PrimaryKeyConstraint("chan", "nick", "time"),
    )

    inspector = inspect(mock_db.engine)
    database.metadata.remove(old_table)
    logger = MagicMock()
    quote.migrate_table(db, logger)
    assert not inspector.has_table(old_table.name)
    assert not inspector.has_table(quote.qtable.name)
    assert logger.mock_calls == []


def test_add_quote(mock_db, freeze_time):
    db = mock_db.session()
    quote.qtable.create(bind=mock_db.engine)
    chan = "#foo"
    target = "bar"
    sender = "baz"
    msg = "Some test quote"
    assert quote.add_quote(db, chan, target, sender, msg) == "Quote added."
    assert mock_db.get_data(quote.qtable) == [
        (chan, target, sender, msg, time.time(), False)
    ]


def test_add_quote_existing(mock_db, freeze_time):
    db = mock_db.session()
    quote.qtable.create(bind=mock_db.engine)

    chan = "#foo"
    target = "bar"
    sender = "baz"
    msg = "Some test quote"
    mock_db.load_data(
        quote.qtable,
        [
            {
                "chan": chan,
                "nick": target,
                "add_nick": sender,
                "msg": msg,
                "time": 0,
            },
        ],
    )
    assert (
        quote.add_quote(db, chan, target, sender, msg)
        == "Message already stored, doing nothing."
    )
    assert mock_db.get_data(quote.qtable) == [
        ("#foo", "bar", "baz", "Some test quote", 0.0, False),
    ]


def test_quote_cmd_add(mock_db, freeze_time):
    db = mock_db.session()
    quote.qtable.create(bind=mock_db.engine)
    chan = "#foo"
    target = "bar"
    sender = "baz"
    msg = "Some test quote"
    text = "add " + target + " " + msg
    event = MagicMock()
    res = quote.quote(text, sender, chan, db, event)
    assert res is None
    assert mock_db.get_data(quote.qtable) == [
        (chan, target, sender, msg, time.time(), False)
    ]
    assert event.mock_calls == [call.notice("Quote added.")]


def test_quote_cmd_get_nick_random(mock_db, freeze_time):
    db = mock_db.session()
    quote.qtable.create(bind=mock_db.engine)
    chan = "#foo"
    target = "bar"
    sender = "baz"
    msg = "Some test quote"
    quote.add_quote(db, chan, target, sender, msg)
    text = target
    event = MagicMock()
    res = quote.quote(text, sender, chan, db, event)
    assert res == "[1/1] <b\u200bar> Some test quote"
    # assert mock_db.get_data(quote.qtable) == [(chan, target, sender, msg, time.time(), False)]
    assert event.mock_calls == []


def test_quote_cmd_get_chan_random(mock_db, freeze_time):
    db = mock_db.session()
    quote.qtable.create(bind=mock_db.engine)
    chan = "#foo"
    target = "bar"
    sender = "baz"
    msg = "Some test quote"
    quote.add_quote(db, chan, target, sender, msg)
    text = chan
    event = MagicMock()
    res = quote.quote(text, sender, chan, db, event)
    assert res == "[1/1] <b\u200bar> Some test quote"
    assert event.mock_calls == []


def test_quote_cmd_get_nick_chan_random(mock_db, freeze_time):
    db = mock_db.session()
    quote.qtable.create(bind=mock_db.engine)
    chan = "#foo"
    target = "bar"
    sender = "baz"
    msg = "Some test quote"
    quote.add_quote(db, chan, target, sender, msg)
    text = chan + " " + target
    event = MagicMock()
    res = quote.quote(text, sender, chan, db, event)
    assert res == "[1/1] <b\u200bar> Some test quote"
    assert event.mock_calls == []
