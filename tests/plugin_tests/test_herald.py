from unittest.mock import MagicMock

import pytest

from cloudbot.event import Event
from plugins import herald
from tests.util import wrap_hook_response


@pytest.fixture()
def clear_cache():
    try:
        yield
    finally:
        herald.herald_cache.clear()


@pytest.fixture()
def unset_timeout():
    try:
        yield
    finally:
        herald.floodcheck.clear()


@pytest.mark.usefixtures("unset_timeout")
class TestWelcome:
    def _run(self):
        conn = MagicMock()
        event = Event(
            hook=MagicMock(),
            bot=conn.bot,
            conn=conn,
            channel='#foo',
            nick='foobaruser'
        )
        return wrap_hook_response(herald.welcome, event)

    def test_no_herald(self):
        result = self._run()
        assert result == []

    @pytest.mark.parametrize('text,out', [
        ('Hello world', '\u200b Hello world'),
        ('bino', '\u200b flenny'),
        ('\u200b hi', '\u200b \u200b hi'),
        ('o\u200b<', 'DECOY DUCK --> o\u200b<'),
    ])
    def test_char_strip(self, clear_cache, text, out):
        herald.herald_cache['#foo']['foobaruser'] = text
        result = self._run()
        assert result == [('message', ('#foo', out))]
