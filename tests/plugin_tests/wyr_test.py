from unittest.mock import MagicMock

import pytest

from plugins import wyr


@pytest.fixture()
def filter_nsfw():
    wyr.FILTERED_TAGS = ("nsfw",)
    try:
        yield
    finally:
        wyr.FILTERED_TAGS = ()


@pytest.mark.parametrize(
    "data,out",
    [
        (
            {
                "title": "title",
                "choicea": "choicea",
                "choiceb": "choiceb",
                "tags": "a,b,c",
                "nsfw": True,
                "link": "baz",
            },
            "Unable to find a would you rather question",
        ),
        (
            {
                "title": "title",
                "choicea": "choicea",
                "choiceb": "choiceb",
                "tags": "",
                "nsfw": False,
                "link": "baz",
            },
            "Title... choicea \x02OR\x02 choiceb? - baz",
        ),
        (
            {
                "title": "title choicea choiceb",
                "choicea": "choicea",
                "choiceb": "choiceb",
                "tags": "",
                "nsfw": False,
                "link": "baz",
            },
            "Would you rather... choicea \x02OR\x02 choiceb? - baz",
        ),
    ],
)
def test_wyr_filtered(mock_requests, filter_nsfw, data, out):
    mock_requests.add("GET", "http://www.rrrather.com/botapi", json=data)
    bot = MagicMock(user_agent="foobar")
    assert wyr.wyr(bot) == out
