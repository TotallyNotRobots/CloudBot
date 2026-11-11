from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import alembic
import alembic.config
import pytest

from cloudbot.db import db_init, get_db_version, get_schema_version
from cloudbot.util import database

if TYPE_CHECKING:
    from tests.util.mock_db import MockDB


@pytest.mark.asyncio
async def test_empty_init(mock_db: MockDB, mock_bot_factory) -> None:
    mock_bot = mock_bot_factory(
        db=mock_db,
        base_dir=Path.cwd(),
        config={
            "connections": [
                {
                    "type": "irc",
                    "name": "foobar",
                    "nick": "TestBot",
                    "channels": [],
                    "connection": {"server": "irc.example.com"},
                }
            ],
            "upgrade_schema": True,
        },
    )

    # Load all remaining unloaded plugins
    mock_bot.plugin_manager.get_plugin_tables(mock_bot.plugin_dir, reload=False)
    assert len(database.metadata.tables) > 10
    assert db_init(mock_bot)


@pytest.mark.asyncio
async def test_init_no_upgrade(
    mock_db: MockDB, mock_bot_factory, caplog_bot: pytest.LogCaptureFixture
) -> None:
    mock_bot = mock_bot_factory(
        db=mock_db,
        base_dir=Path.cwd(),
        config={
            "connections": [
                {
                    "type": "irc",
                    "name": "foobar",
                    "nick": "TestBot",
                    "channels": [],
                    "connection": {"server": "irc.example.com"},
                }
            ]
        },
    )

    # Load all remaining unloaded plugins
    mock_bot.plugin_manager.get_plugin_tables(mock_bot.plugin_dir, reload=False)
    assert len(database.metadata.tables) > 10
    assert not db_init(mock_bot)
    assert caplog_bot.record_tuples == [
        (
            "cloudbot",
            50,
            "Database schema is out of date and auto-updating is disabled! Use "
            '`alembic upgrade heads` or set `"upgrade_schema": true` in the '
            "config. NOTE: ALWAYS take a backup of the database before upgrading!",
        )
    ]


@pytest.mark.asyncio
async def test_get_db_version(
    mock_db: MockDB, mock_bot_factory, caplog_bot
) -> None:
    mock_bot = mock_bot_factory(
        db=mock_db,
        base_dir=Path.cwd(),
        config={
            "connections": [
                {
                    "type": "irc",
                    "name": "foobar",
                    "nick": "TestBot",
                    "channels": [],
                    "connection": {"server": "irc.example.com"},
                }
            ]
        },
    )

    # Load all remaining unloaded plugins
    mock_bot.plugin_manager.get_plugin_tables(mock_bot.plugin_dir, reload=False)
    cfg = alembic.config.Config(
        "alembic.ini", "pyproject.toml", attributes={"bot": mock_bot}
    )
    assert get_db_version(cfg) == ""


@pytest.mark.asyncio
async def test_get_schema_version(
    mock_db: MockDB, mock_bot_factory, caplog_bot
) -> None:
    original_cwd = Path.cwd().resolve()
    mock_bot = mock_bot_factory(
        db=mock_db,
        base_dir=Path.cwd(),
        config={
            "connections": [
                {
                    "type": "irc",
                    "name": "foobar",
                    "nick": "TestBot",
                    "channels": [],
                    "connection": {"server": "irc.example.com"},
                }
            ]
        },
    )

    # Load all remaining unloaded plugins
    mock_bot.plugin_manager.get_plugin_tables(mock_bot.plugin_dir, reload=False)
    cfg = alembic.config.Config(
        Path.cwd() / "alembic.ini",
        Path.cwd() / "pyproject.toml",
        attributes={"bot": mock_bot},
    )
    assert Path.cwd().resolve() == original_cwd
    assert get_schema_version(cfg) != ""
