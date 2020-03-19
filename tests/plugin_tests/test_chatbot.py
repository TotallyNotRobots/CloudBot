from unittest.mock import MagicMock

from cloudbot.config import Config


class MockConfig(Config):
    def load_config(self):
        self._api_keys.clear()


class MockBot:
    def __init__(self, config):
        self.config = MockConfig(self, config)


def test_make_api():
    from plugins import chatbot
    from plugins.chatbot import make_api
    bot = MockBot({'api_keys': {'cleverbot': 'testapikey'}})
    make_api(bot)
    assert chatbot.container.api.key == 'testapikey'


def test_chitchat():
    from plugins import chatbot
    from plugins.chatbot import chitchat

    chatbot.container.api = None

    assert chitchat('foobar') == "Please add an API key from http://www.cleverbot.com/api to enable this feature."

    mock_api = MagicMock()
    chatbot.container.api = mock_api

    chitchat('foobar123')

    mock_api.say.assert_called_with('foobar123')
