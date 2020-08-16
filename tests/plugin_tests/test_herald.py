from datetime import timedelta
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
        herald.user_join.clear()


class TestWelcome:
    def _run(self):
        conn = MagicMock()
        event = Event(
            hook=MagicMock(), bot=conn.bot, conn=conn, channel="#foo", nick="foobaruser"
        )
        return wrap_hook_response(herald.welcome, event)

    def test_no_herald(self, clear_cache):
        result = self._run()
        assert result == []

    @pytest.mark.parametrize(
        "text,out",
        [
            ("Hello world", "\u200b Hello world"),
            ("bino", "\u200b flenny"),
            ("\u200b hi", "\u200b \u200b hi"),
            ("o\u200b<", "DECOY DUCK --> o\u200b<"),
        ],
    )
    def test_char_strip(self, clear_cache, text, out):
        herald.herald_cache["#foo"]["foobaruser"] = text
        result = self._run()
        assert result == [("message", ("#foo", out))]

    def test_flood(self, clear_cache, freeze_time):
        chan = "#foo"
        nick = "foobaruser"
        nick1 = "foonick"
        chan1 = "#barchan"
        herald.herald_cache[chan].update({nick: "Some herald", nick1: "Other herald,"})
        herald.herald_cache[chan1].update(
            {nick: "Someother herald", nick1: "Yet another herald"}
        )
        conn = MagicMock(name="fooconn")
        conn.mock_add_spec(["name", "bot", "action", "message", "notice"])
        event = Event(conn=conn, bot=conn.bot, channel=chan, nick=nick)
        event1 = Event(conn=conn, bot=conn.bot, channel=chan, nick=nick1)
        event2 = Event(conn=conn, bot=conn.bot, channel=chan1, nick=nick,)
        event3 = Event(conn=conn, bot=conn.bot, channel=chan1, nick=nick1)

        def check(ev):
            return wrap_hook_response(herald.welcome, ev)

        assert check(event) == [("message", ("#foo", "\u200b Some herald"))]

        assert check(event) == []
        assert check(event1) == []

        assert check(event2) == [("message", ("#barchan", "\u200b Someother herald"))]
        assert check(event3) == []

        freeze_time.tick(timedelta(seconds=10))
        # Channel spam time expired
        assert check(event1) == [("message", ("#foo", "\u200b Other herald,"))]
        # User spam time still in effect
        assert check(event) == []

        freeze_time.tick(timedelta(minutes=5))

        # User spam time expired
        assert check(event) == [("message", ("#foo", "\u200b Some herald"))]
