import textwrap
from unittest.mock import patch

import pytest

from cloudbot import config


@pytest.mark.parametrize('text,result', (
        ('connection', 'connection'),
        ('c onn ection', 'c_onn_ection'),
        ('c+onn ection', 'conn_ection'),
))
def test_clean_name(text, result):
    from cloudbot.bot import clean_name
    assert clean_name(text) == result


class MockConn:
    def __init__(self, nick=None):
        self.nick = nick
        self.config = {}


def test_get_cmd_regex():
    from cloudbot.bot import get_cmd_regex
    from cloudbot.event import Event
    event = Event(channel='TestUser', nick='TestUser', conn=MockConn('Bot'))
    regex = get_cmd_regex(event)
    assert textwrap.dedent(regex.pattern) == textwrap.dedent(r"""
    ^
    # Prefix or nick
    (?:
        (?P<prefix>[\.])?
        |
        Bot[,;:]+\s+
    )
    (?P<command>\w+)  # Command
    (?:$|\s+)
    (?P<text>.*)     # Text
    """)


class MockConfig(config.Config):
    def load_config(self):
        self.update({
            'connections': [
                {
                    'type': 'irc',
                    'name': 'foobar',
                    'nick': 'TestBot',
                    'channels': [],
                    'connection': {
                        'server': 'irc.example.com'
                    }
                }
            ]
        })


def test_load_clients():
    with patch('cloudbot.bot.Config', new=MockConfig):
        from cloudbot.bot import CloudBot
        bot = CloudBot()
        assert bot.connections['foobar'].nick == 'TestBot'
        assert bot.connections['foobar'].type == 'irc'
