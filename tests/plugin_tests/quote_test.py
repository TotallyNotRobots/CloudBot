import time
from unittest.mock import MagicMock, call

from plugins import quote


def test_add_quote(mock_db, freeze_time):
    db = mock_db.session()
    quote.qtable.create(bind=mock_db.engine)
    chan = "#foo"
    target = "bar"
    sender = "baz"
    msg = "Some test quote"
    quote.add_quote(db, chan, target, sender, msg)
    assert mock_db.get_data(quote.qtable) == [
        (chan, target, sender, msg, time.time(), False)
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
