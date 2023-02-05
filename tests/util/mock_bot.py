import logging
from typing import Awaitable, Dict, Optional

from watchdog.observers import Observer

from cloudbot.bot import CloudBot
from cloudbot.client import Client
from cloudbot.plugin import PluginManager
from cloudbot.util.async_util import create_future
from tests.util.mock_config import MockConfig
from tests.util.mock_db import MockDB


class MockBot:
    def __init__(
        self,
        *,
        config=None,
        loop=None,
        db: Optional[MockDB] = None,
        base_dir=None,
    ):
        self.old_db = None
        self.do_db_migrate = False
        self.loop = loop
        self.base_dir = base_dir
        self.data_path = self.base_dir / "data"
        self.data_dir = str(self.data_path)
        self.plugin_dir = self.base_dir / "plugins"
        if self.loop:
            self.stopped_future: Awaitable[bool] = create_future(self.loop)
        else:
            self.stopped_future = None

        if db:
            self.db_engine = db.engine
        else:
            self.db_engine = None

        self.running = True
        self.logger = logging.getLogger("cloudbot")
        self.config = MockConfig(self)

        if config is not None:
            self.config.update(config)

        self.plugin_manager = PluginManager(self)
        self.plugin_reloading_enabled = False
        self.config_reloading_enabled = False
        self.observer = Observer()
        self.repo_link = "https://github.com/foobar/baz"
        self.user_agent = "User agent"
        self.connections: Dict[str, Client] = {}

    def close(self):
        self.observer.stop()

    def migrate_db(self) -> None:
        return CloudBot.migrate_db(self)  # type: ignore[arg-type]
