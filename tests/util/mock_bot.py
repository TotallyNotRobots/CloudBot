import asyncio

from cloudbot.config import Config


class MockConfig(Config):
    def load_config(self):
        self._api_keys.clear()

    def add_api_key(self, name, value):
        self._api_keys[name] = value


class MockBot:
    def __init__(self, config, loop=None, db=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        self.loop = loop
        self.config = MockConfig(self, config)
        if db:
            self.db_session = db.session
        else:
            self.db_session = None

        self.repo_link = "https://github.com/TotallyNotRobots/CloudBot"
