import importlib

import pytest
from requests import HTTPError

from plugins import bible
from tests.util import run_cmd


def test_bible(mock_requests):
    importlib.reload(bible)
    mock_requests.add(
        "GET",
        "https://labs.bible.org/api?passage=gen+1%3A1&formatting=plain&type"
        "=json",
        json=[
            {
                "bookname": "Genesis",
                "chapter": "1",
                "verse": "1",
                "text": "In the beginning God created the heavens and the "
                "earth.",
                "title": "The Creation of the World",
                "titles": ["The Creation of the World"],
            }
        ],
    )
    assert run_cmd(bible.bible, "bible", "gen 1:1") == [
        (
            "return",
            "\x02Genesis 1:1\x02 In the beginning God created the heavens and "
            "the earth.",
        )
    ]


def test_bible_exc(mock_requests):
    importlib.reload(bible)
    mock_requests.add(
        "GET",
        "https://labs.bible.org/api?passage=gen+1%3A1&formatting=plain&type"
        "=json",
        status=500,
    )
    results = []
    with pytest.raises(HTTPError):
        assert run_cmd(bible.bible, "bible", "gen 1:1", results=results)

    assert results == [
        (
            "message",
            (
                "#foo",
                "(foonick) Something went wrong, either you entered an "
                "invalid passage or the API is down.",
            ),
        )
    ]
