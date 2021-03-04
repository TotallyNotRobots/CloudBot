import logging
from typing import Optional

from watchdog.observers import Observer

from cloudbot.plugin import PluginManager
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
        self.base_dir = base_dir
        self.data_path = self.base_dir / "data"
        self.data_dir = str(self.data_path)
        self.plugin_dir = self.base_dir / "plugins"

        if db:
            self.db_session = db.session
            self.db_engine = db.engine
        else:
            self.db_session = None
            self.db_engine = None

        self.running = True
        self.logger = logging.getLogger("cloudbot")
        self.loop = loop
        self.config = MockConfig(self)

        if config is not None:
            self.config.update(config)

        self.plugin_manager = PluginManager(self)
        self.plugin_reloading_enabled = False
        self.config_reloading_enabled = False
        self.observer = Observer()
        self.repo_link = "https://github.com/foobar/baz"
        self.user_agent = "User agent"

    def close(self):
        self.observer.stop()
