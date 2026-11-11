import time
from unittest.mock import MagicMock, call

from plugins import quote


def test_add_quote(mock_db, freeze_time) -> None:
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


def test_add_quote_existing(mock_db, freeze_time) -> None:
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
            }
        ],
    )
    assert (
        quote.add_quote(db, chan, target, sender, msg)
        == "Message already stored, doing nothing."
    )
    assert mock_db.get_data(quote.qtable) == [
        ("#foo", "bar", "baz", "Some test quote", 0.0, False)
    ]


def test_quote_cmd_add(mock_db, freeze_time) -> None:
    db = mock_db.session()
    quote.qtable.create(bind=mock_db.engine)
    chan = "#foo"
    target = "bar"
    sender = "baz"
    msg = "Some test quote"
    text = f"add {target} {msg}"
    event = MagicMock()
    res = quote.quote(text, sender, chan, db, event)
    assert res is None
    assert mock_db.get_data(quote.qtable) == [
        (chan, target, sender, msg, time.time(), False)
    ]
    assert event.mock_calls == [call.notice("Quote added.")]


def test_quote_cmd_get_nick_random(mock_db, freeze_time) -> None:
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


def test_quote_cmd_get_chan_random(mock_db, freeze_time) -> None:
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


def test_quote_cmd_get_nick_chan_random(mock_db, freeze_time) -> None:
    db = mock_db.session()
    quote.qtable.create(bind=mock_db.engine)
    chan = "#foo"
    target = "bar"
    sender = "baz"
    msg = "Some test quote"
    quote.add_quote(db, chan, target, sender, msg)
    text = f"{chan} {target}"
    event = MagicMock()
    res = quote.quote(text, sender, chan, db, event)
    assert res == "[1/1] <b\u200bar> Some test quote"
    assert event.mock_calls == []
