from unittest.mock import call

import pytest

from plugins.core import autojoin
from tests.util.mock_conn import MockConn


def test_add_chan(mock_db):
    autojoin.chan_cache.clear()
    autojoin.table.create(mock_db.engine)
    db = mock_db.session()
    conn = MockConn()
    chan = "#foo"
    nick = conn.nick
    autojoin.add_chan(db, conn, chan, nick)
    assert mock_db.get_data(autojoin.table) == [("testconn", "#foo")]


def test_add_chan_again(mock_db):
    autojoin.chan_cache.clear()
    autojoin.table.create(mock_db.engine)
    db = mock_db.session()
    conn = MockConn()
    chan = "#foo"
    nick = conn.nick
    autojoin.add_chan(db, conn, chan, nick)
    autojoin.chan_cache.clear()
    autojoin.add_chan(db, conn, chan, nick)
    assert mock_db.get_data(autojoin.table) == [("testconn", "#foo")]


def test_add_chan_other_nick(mock_db):
    autojoin.chan_cache.clear()
    autojoin.table.create(mock_db.engine)
    db = mock_db.session()
    conn = MockConn()
    chan = "#foo"
    nick = "other"
    autojoin.add_chan(db, conn, chan, nick)
    assert mock_db.get_data(autojoin.table) == []


def test_kick(mock_db):
    autojoin.chan_cache.clear()
    autojoin.table.create(mock_db.engine)
    conn = MockConn()
    chan = "#foo"
    db = mock_db.session()
    mock_db.add_row(autojoin.table, conn=conn.name.lower(), chan=chan.lower())
    autojoin.load_cache(db)
    target = conn.nick
    autojoin.on_kick(db, conn, chan, target)
    assert mock_db.get_data(autojoin.table) == []


def test_kick_other(mock_db):
    autojoin.chan_cache.clear()
    autojoin.table.create(mock_db.engine)
    conn = MockConn()
    chan = "#foo"
    db = mock_db.session()
    mock_db.add_row(autojoin.table, conn=conn.name.lower(), chan=chan.lower())
    autojoin.load_cache(db)
    target = "other"
    autojoin.on_kick(db, conn, chan, target)
    assert mock_db.get_data(autojoin.table) == [("testconn", "#foo")]


@pytest.mark.asyncio()
async def test_joins(mock_db):
    autojoin.chan_cache.clear()
    autojoin.table.create(mock_db.engine)
    conn = MockConn()
    chan = "#foo"
    db = mock_db.session()
    mock_db.add_row(autojoin.table, conn=conn.name.lower(), chan=chan.lower())

    autojoin.load_cache(db)
    await autojoin.do_joins(conn)
    assert conn.join.mock_calls == [call("#foo")]
