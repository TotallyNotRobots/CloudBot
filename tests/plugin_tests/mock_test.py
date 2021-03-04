from unittest.mock import MagicMock, call

from plugins import mock
from tests.util.mock_conn import MockConn


def test_mock_no_message():
    conn = MockConn()
    event = MagicMock()
    res = mock.mock("bar", "#foo", conn, event.message)
    assert res == "Nothing found in recent history for bar"
    assert event.mock_calls == []


def test_mock_no_matching_message():
    conn = MockConn()
    event = MagicMock()
    chan = "#foo"
    target = "bar"
    conn.history[chan] = [("baz", 123, "Hello this is a test")]
    res = mock.mock(target, chan, conn, event.message)
    assert res == "Nothing found in recent history for bar"
    assert event.mock_calls == []


def test_mock():
    conn = MockConn()
    chan = "#foo"
    target = "bar"
    conn.history[chan] = [(target, 123, "Hello this is a test")]
    event = MagicMock()
    res = mock.mock(target, chan, conn, event.message)
    assert res is None
    assert event.mock_calls == [call.message("<bar> hElLo tHiS Is a tEsT")]


def test_mock_action():
    conn = MockConn()
    chan = "#foo"
    target = "bar"
    conn.history[chan] = [(target, 123, "\1ACTION Hello this is a test\1")]
    event = MagicMock()
    res = mock.mock(target, chan, conn, event.message)
    assert res is None
    assert event.mock_calls == [call.message("* bar hElLo tHiS Is a tEsT")]
