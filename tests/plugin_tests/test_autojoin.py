from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import call

import pytest

from plugins.core import autojoin
from tests.util.mock_conn import MockClient

if TYPE_CHECKING:
    from tests.util.mock_bot import MockBotFactory
    from tests.util.mock_db import MockDB


@pytest.mark.asyncio
async def test_add_chan(
    mock_db: MockDB, mock_bot_factory: MockBotFactory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    autojoin.chan_cache.clear()
    mock_db.create_table(autojoin.Autojoin)
    db = mock_db.session()
    conn = MockClient(bot=bot)
    chan = "#foo"
    nick = conn.nick
    autojoin.add_chan(db, conn, chan, nick)
    assert mock_db.get_data(autojoin.Autojoin) == [("testconn", "#foo")]


@pytest.mark.asyncio
async def test_add_chan_again(
    mock_db: MockDB, mock_bot_factory: MockBotFactory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    autojoin.chan_cache.clear()
    mock_db.create_table(autojoin.Autojoin)
    db = mock_db.session()
    conn = MockClient(bot=bot)
    chan = "#foo"
    nick = conn.nick
    autojoin.add_chan(db, conn, chan, nick)
    autojoin.chan_cache.clear()
    autojoin.add_chan(db, conn, chan, nick)
    assert mock_db.get_data(autojoin.Autojoin) == [("testconn", "#foo")]


@pytest.mark.asyncio
async def test_add_chan_other_nick(
    mock_db: MockDB, mock_bot_factory: MockBotFactory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    autojoin.chan_cache.clear()
    mock_db.create_table(autojoin.Autojoin)
    db = mock_db.session()
    conn = MockClient(bot=bot)
    chan = "#foo"
    nick = "other"
    autojoin.add_chan(db, conn, chan, nick)
    assert mock_db.get_data(autojoin.Autojoin) == []


@pytest.mark.asyncio
async def test_kick(mock_db: MockDB, mock_bot_factory: MockBotFactory) -> None:
    bot = mock_bot_factory(db=mock_db)
    autojoin.chan_cache.clear()
    mock_db.create_table(autojoin.Autojoin)
    conn = MockClient(bot=bot)
    chan = "#foo"
    db = mock_db.session()
    mock_db.add_row(
        autojoin.Autojoin, conn=conn.name.lower(), chan=chan.lower()
    )
    autojoin.load_cache(db)
    target = conn.nick
    autojoin.on_kick(db, conn, chan, target)
    assert mock_db.get_data(autojoin.Autojoin) == []


@pytest.mark.asyncio
async def test_kick_other(
    mock_db: MockDB, mock_bot_factory: MockBotFactory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    autojoin.chan_cache.clear()
    mock_db.create_table(autojoin.Autojoin)
    conn = MockClient(bot=bot)
    chan = "#foo"
    db = mock_db.session()
    mock_db.add_row(
        autojoin.Autojoin, conn=conn.name.lower(), chan=chan.lower()
    )
    autojoin.load_cache(db)
    target = "other"
    autojoin.on_kick(db, conn, chan, target)
    assert mock_db.get_data(autojoin.Autojoin) == [("testconn", "#foo")]


@pytest.mark.asyncio
async def test_joins(mock_db: MockDB, mock_bot_factory: MockBotFactory) -> None:
    bot = mock_bot_factory(db=mock_db)
    autojoin.chan_cache.clear()
    mock_db.create_table(autojoin.Autojoin)
    conn = MockClient(bot=bot)
    chan = "#foo"
    db = mock_db.session()
    mock_db.add_row(
        autojoin.Autojoin, conn=conn.name.lower(), chan=chan.lower()
    )

    autojoin.load_cache(db)
    await autojoin.do_joins(conn)
    assert conn.mock_calls() == [call.join("#foo", None)]
