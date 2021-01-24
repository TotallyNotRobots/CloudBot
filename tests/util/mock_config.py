from cloudbot.config import Config


class MockConfig(Config):
    def load_config(self):
        self._api_keys.clear()
