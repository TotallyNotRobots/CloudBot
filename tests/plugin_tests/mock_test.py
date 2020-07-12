from unittest.mock import MagicMock, call

from plugins import mock


def test_mock():
    conn = MagicMock(history={})
    event = MagicMock()
    nothing_found = "Nothing found in recent history for foonick"
    assert (
        mock.mock("foonick", "#foochan", conn, event.message) == nothing_found
    )
    assert event.message.mock_calls == []

    conn = MagicMock(history={"#foochan": []})
    event = MagicMock()
    assert (
        mock.mock("foonick", "#foochan", conn, event.message) == nothing_found
    )
    assert event.message.mock_calls == []

    conn = MagicMock(history={"#foochan": [("foonick", 1, "foobar")]})
    event = MagicMock()
    assert mock.mock("foonick", "#foochan", conn, event.message) is None
    assert event.message.mock_calls == [call("<foonick> fOoBaR")]

    conn = MagicMock(history={"#foochan": [("foonick", 1, "\x01ACTIONfoobar")]})
    event = MagicMock()
    assert mock.mock("foonick", "#foochan", conn, event.message) is None
    assert event.message.mock_calls == [call("* foonick fOoBaR")]

    conn = MagicMock(
        history={"#foochan": [("foonick", 1, "\x01ACTION foobar")]}
    )
    event = MagicMock()
    assert mock.mock("foonick", "#foochan", conn, event.message) is None
    assert event.message.mock_calls == [call("* foonick fOoBaR")]
