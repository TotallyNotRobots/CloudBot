from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call

from plugins import mock as mock_plugin
from tests.util.mock_conn import MockClient

if TYPE_CHECKING:
    from tests.util.mock_bot import MockBot


def test_mock_no_message(mock_bot: MockBot) -> None:
    conn = MockClient(bot=mock_bot)
    event = MagicMock()
    res = mock_plugin.mock("bar", "#foo", conn, event.message)
    assert res == "Nothing found in recent history for bar"
    assert event.mock_calls == []


def test_mock_no_matching_message(mock_bot: MockBot) -> None:
    conn = MockClient(bot=mock_bot)
    event = MagicMock()
    chan = "#foo"
    target = "bar"
    conn.history[chan] = deque([("baz", 123, "Hello this is a test")])
    res = mock_plugin.mock(target, chan, conn, event.message)
    assert res == "Nothing found in recent history for bar"
    assert event.mock_calls == []


def test_mock(mock_bot: MockBot) -> None:
    conn = MockClient(bot=mock_bot)
    chan = "#foo"
    target = "bar"
    conn.history[chan] = deque([(target, 123, "Hello this is a test")])
    event = MagicMock()
    res = mock_plugin.mock(target, chan, conn, event.message)
    assert res is None
    assert event.mock_calls == [call.message("<bar> hElLo tHiS Is a tEsT")]


def test_mock_action(mock_bot: MockBot) -> None:
    conn = MockClient(bot=mock_bot)
    chan = "#foo"
    target = "bar"
    conn.history[chan] = deque(
        [(target, 123, "\1ACTION Hello this is a test\1")]
    )
    event = MagicMock()
    res = mock_plugin.mock(target, chan, conn, event.message)
    assert res is None
    assert event.mock_calls == [call.message("* bar hElLo tHiS Is a tEsT")]
