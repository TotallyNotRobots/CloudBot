from unittest.mock import MagicMock

from cloudbot.clients.irc import IrcClient


class MockIrcClient(IrcClient):
    def __init__(self, bot, name, nick, config):
        super().__init__(bot, "irc", name, nick, config=config)
        self.connect = MagicMock()
        self.send = MagicMock()
