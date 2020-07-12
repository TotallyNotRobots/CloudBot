from unittest.mock import MagicMock

import pytest

from cloudbot.event import CommandEvent
from plugins import soundcloud
from tests.util import wrap_hook_response


def test_soundcloud_connection_error(mock_requests, mock_api_keys):
    mock_requests.add(
        "GET",
        "http://api.soundcloud.com/tracks/?client_id=APIKEY&q=foobar",
        status=502,
    )
    event = CommandEvent(
        channel="#foo",
        text="foobar",
        triggered_command="soundcloud",
        cmd_prefix=".",
        hook=MagicMock(),
        conn=MagicMock(),
    )
    res = []
    with pytest.raises(soundcloud.APIError):
        wrap_hook_response(soundcloud.soundcloud, event, res)

    assert res == [
        (
            "message",
            (
                "#foo",
                "(None) Could not find tracks: 502 Server Error: Bad Gateway "
                "for url: http://api.soundcloud.com/tracks/?"
                "client_id=APIKEY&q=foobar",
            ),
        )
    ]


def test_soundcloud_no_results(mock_requests, mock_api_keys):
    mock_requests.add(
        "GET",
        "http://api.soundcloud.com/tracks/?q=foobar&client_id=APIKEY",
        json={},
    )
    event = CommandEvent(
        channel="#foo",
        text="foobar",
        triggered_command="soundcloud",
        cmd_prefix=".",
        hook=MagicMock(),
        conn=MagicMock(),
    )
    res = wrap_hook_response(soundcloud.soundcloud, event)
    assert res == [("return", "No results found.")]
