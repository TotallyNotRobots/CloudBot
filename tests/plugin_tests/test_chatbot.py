from unittest.mock import MagicMock

from plugins import chatbot


def test_make_api(mock_bot_factory, event_loop):
    bot = mock_bot_factory(
        config={"api_keys": {"cleverbot": "testapikey"}}, loop=event_loop
    )
    chatbot.make_api(bot)
    assert chatbot.container.api.key == "testapikey"


def test_chitchat():
    chatbot.container.api = None

    assert (
        chatbot.chitchat("foobar")
        == "Please add an API key from http://www.cleverbot.com/api to enable this feature."
    )

    mock_api = MagicMock()
    chatbot.container.api = mock_api

    chatbot.chitchat("foobar123")

    mock_api.say.assert_called_with("foobar123")
