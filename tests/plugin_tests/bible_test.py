from unittest.mock import MagicMock, call

import pytest
from requests import HTTPError

from plugins import bible


def test_bible(mock_requests):
    mock_requests.add(
        "GET",
        "https://labs.bible.org/api?passage=foo&formatting=plain&type=json",
        json=[
            {
                "bookname": "foo",
                "chapter": 12,
                "verse": 54,
                "text": "things and stuff",
            }
        ],
    )
    event = MagicMock()
    res = bible.bible("foo", event.reply)
    assert res == "\x02foo 12:54\x02 things and stuff"
    assert event.mock_calls == []


def test_bible_404(mock_requests):
    mock_requests.add(
        "GET",
        "https://labs.bible.org/api?passage=foo&formatting=plain&type=json",
        status=404,
    )
    event = MagicMock()
    with pytest.raises(HTTPError):
        bible.bible("foo", event.reply)

    assert event.mock_calls == [
        call.reply(
            "Something went wrong, either you entered an invalid passage or the API is down."
        )
    ]
