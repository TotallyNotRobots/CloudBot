import asyncio

from cloudbot.config import Config


class MockConfig(Config):
    def load_config(self):
        self._api_keys.clear()


class MockBot:
    def __init__(self, config, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        self.loop = loop
        self.config = MockConfig(self, config)
