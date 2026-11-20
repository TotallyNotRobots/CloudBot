from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from watchdog.observers import Observer

from cloudbot.bot import AbstractBot, CloudBot
from cloudbot.plugin import PluginManager
from tests.util.mock_config import MockConfig

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from collections.abc import Awaitable
    from pathlib import Path

    from sqlalchemy.engine.base import Engine

    from cloudbot.client import Client
    from tests.util.mock_db import MockDB


class MockBot(AbstractBot):
    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        loop: AbstractEventLoop | None = None,
        db: MockDB | None = None,
        base_dir: Path,
    ) -> None:
        self.old_db = None
        self.do_db_migrate = False
        self.base_dir = base_dir
        self.data_path = self.base_dir / "data"
        self.data_dir = str(self.data_path)
        self.plugin_dir = self.base_dir / "plugins"
        if loop:
            self.stopped_future: Awaitable[bool] | None = loop.create_future()
        else:
            self.stopped_future = None

        if db:
            self.db_engine: Engine | None = db.engine
        else:
            self.db_engine = None

        self.running = True
        self.logger = logging.getLogger("cloudbot")
        super().__init__(config=MockConfig(), loop=loop)

        if config is not None:
            self.config.update(config)

        self._plugin_manager = PluginManager(self)
        self.plugin_reloading_enabled = False
        self.config_reloading_enabled = False
        self.observer = Observer()
        self.repo_link = "https://github.com/foobar/baz"
        self.user_agent = "User agent"
        self.connections: dict[str, Client] = {}

    def get_plugin_manager(self) -> PluginManager:
        return self._plugin_manager

    def close(self) -> None:
        self.observer.stop()

    def migrate_db(self, *, old_db_url: str) -> None:
        return CloudBot.migrate_db(self, old_db_url=old_db_url)  # type: ignore[arg-type]


MockBotFactory = Callable[..., MockBot]
