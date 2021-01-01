import asyncio
import logging
from pathlib import Path
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
        if base_dir:
            self.base_dir = base_dir
        else:
            self.base_dir = Path().resolve()

        if loop is None:
            loop = asyncio.get_event_loop()

        if db:
            self.db_session = db.session
            self.db_engine = db.engine
        else:
            self.db_session = None
            self.db_engine = None

        self.base_dir = Path().resolve()
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
