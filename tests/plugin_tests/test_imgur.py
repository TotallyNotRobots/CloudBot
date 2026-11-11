from __future__ import annotations

import random
from typing import TYPE_CHECKING

import responses
from responses.matchers import query_param_matcher

from plugins import imgur

if TYPE_CHECKING:
    from responses import RequestsMock


def test_imgur_no_api(mock_requests: RequestsMock, mock_api_keys) -> None:
    mock_api_keys.config.get_api_key.return_value = None
    imgur.set_api(mock_api_keys)
    response = imgur.imgur("aries")

    assert response == "No imgur API details"


def test_imgur_no_results(mock_requests: RequestsMock, mock_api_keys) -> None:
    random.seed(0)
    mock_requests.add(responses.GET, "https://api.imgur.com/3/credits", json={})

    mock_requests.add(
        responses.GET,
        "https://api.imgur.com/3/gallery/search/time/all/4?q=foobar",
        json=[],
    )

    imgur.set_api(mock_api_keys)
    response = imgur.imgur("foobar")

    assert response == "No results found."


def test_imgur_meme(mock_requests: RequestsMock, mock_api_keys) -> None:
    random.seed(0)
    mock_requests.add(responses.GET, "https://api.imgur.com/3/credits", json={})

    mock_requests.add(
        responses.GET,
        "https://api.imgur.com/3/gallery/search/time/all/4",
        match=[query_param_matcher({"q": "foobar"})],
        json=[
            {
                "is_album": False,
                "title": "foo",
                "meme_metadata": {"meme_name": "foo"},
                "section": "",
                "nsfw": True,
                "link": "foo.bar",
            },
            {
                "is_album": True,
                "title": "bar",
                "section": "section",
                "nsfw": False,
                "link": "bar.baz",
            },
            {
                "is_album": False,
                "title": "",
                "section": "",
                "nsfw": True,
                "link": "foo.invalid",
            },
        ],
    )

    imgur.set_api(mock_api_keys)
    response = imgur.imgur("foobar")

    assert response == '[\2nsfw\2] "\2foo\2 - foo" - foo.bar'


def test_imgur_reddit(mock_requests: RequestsMock, mock_api_keys) -> None:
    random.seed(0)
    mock_requests.add(responses.GET, "https://api.imgur.com/3/credits", json={})

    mock_requests.add(
        responses.GET,
        "https://api.imgur.com/3/gallery/r/foobar/time/0",
        json=[
            {
                "is_album": False,
                "title": "foo",
                "meme_metadata": {"meme_name": "foo"},
                "section": "",
                "nsfw": True,
                "link": "foo.bar",
            },
            {
                "is_album": True,
                "title": "bar",
                "section": "section",
                "nsfw": False,
                "link": "bar.baz",
                "reddit_comments": "/abc123",
            },
            {
                "is_album": False,
                "title": "",
                "section": "",
                "nsfw": True,
                "link": "foo.invalid",
            },
        ],
    )

    imgur.set_api(mock_api_keys)
    response = imgur.imgur("/r/foobar")

    assert (
        response == '[\2section\2] "bar" - bar.baz (http://reddit.com/abc123)'
    )


def test_imgur_user(mock_requests: RequestsMock, mock_api_keys) -> None:
    random.seed(0)
    mock_requests.add(responses.GET, "https://api.imgur.com/3/credits", json={})

    mock_requests.add(
        responses.GET,
        "https://api.imgur.com/3/gallery/search/time/all/4",
        match=[query_param_matcher({"q": "/u/foobar"})],
        json=[
            {
                "is_album": False,
                "title": "foo",
                "meme_metadata": {"meme_name": "foo"},
                "section": "",
                "nsfw": True,
                "link": "foo.bar",
            },
            {
                "is_album": True,
                "title": "bar",
                "section": "section",
                "nsfw": False,
                "link": "bar.baz",
            },
            {
                "is_album": False,
                "title": "",
                "section": "",
                "nsfw": True,
                "link": "foo.invalid",
            },
        ],
    )

    imgur.set_api(mock_api_keys)
    response = imgur.imgur("/u/foobar")

    assert response == '[\2nsfw\2] "\2foo\2 - foo" - foo.bar'


def test_imgur_random(mock_requests: RequestsMock, mock_api_keys) -> None:
    random.seed(0)
    mock_requests.add(responses.GET, "https://api.imgur.com/3/credits", json={})

    mock_requests.add(
        responses.GET,
        "https://api.imgur.com/3/gallery/random/random/25",
        json=[
            {
                "is_album": False,
                "title": "foo",
                "meme_metadata": {"meme_name": "foo"},
                "section": "",
                "nsfw": True,
                "link": "foo.bar",
            },
            {
                "is_album": True,
                "title": "bar",
                "section": "section",
                "nsfw": False,
                "link": "bar.baz",
            },
            {
                "is_album": False,
                "title": "",
                "section": "",
                "nsfw": True,
                "link": "foo.invalid",
            },
        ],
    )

    imgur.set_api(mock_api_keys)
    response = imgur.imgur("random")

    assert response == '[\2nsfw\2] "\2foo\2 - foo" - foo.bar'


def test_imgur(mock_requests: RequestsMock, mock_api_keys) -> None:
    random.seed(0)
    mock_requests.add(responses.GET, "https://api.imgur.com/3/credits", json={})

    mock_requests.add(
        responses.GET,
        "https://api.imgur.com/3/gallery/hot/viral/0",
        match=[query_param_matcher({"showViral": "true"})],
        json=[
            {
                "is_album": False,
                "title": "foo",
                "meme_metadata": {"meme_name": "foo"},
                "section": "",
                "nsfw": True,
                "link": "foo.bar",
            },
            {
                "is_album": True,
                "title": "bar",
                "section": "section",
                "nsfw": False,
                "link": "bar.baz",
            },
            {
                "is_album": False,
                "title": "",
                "section": "",
                "nsfw": True,
                "link": "foo.invalid",
            },
        ],
    )

    imgur.set_api(mock_api_keys)
    response = imgur.imgur("")

    assert response == '[\2section\2] "bar" - bar.baz'
