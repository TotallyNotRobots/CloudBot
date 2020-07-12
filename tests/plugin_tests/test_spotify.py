import importlib
from datetime import datetime
from unittest.mock import MagicMock, call

import pytest
from requests import HTTPError

from plugins import spotify


@pytest.mark.parametrize(
    "text,item_type,item_id",
    [("open.spotify.com/user/foobar", "user", "foobar"),],
)
def test_http_re(text, item_type, item_id):
    match = spotify.http_re.search(text)
    assert match and match.group(2) == item_type and match.group(3) == item_id


@pytest.mark.parametrize(
    "text,item_type,item_id", [("spotify:user:foobar", "user", "foobar")]
)
def test_spotify_re(text, item_type, item_id):
    match = spotify.spotify_re.search(text)
    assert match and match.group(2) == item_type and match.group(3) == item_id


@pytest.mark.parametrize(
    "data,item_type,output",
    [
        [
            {
                "display_name": "linuxdaemon",
                "external_urls": {
                    "spotify": "https://open.spotify.com/user/7777"
                },
                "followers": {"total": 2500},
                "uri": "spotify:user:7777",
            },
            "user",
            "\x02linuxdaemon\x02, Followers: \x022,500\x02",
        ],
        [
            {
                "name": "foobar",
                "artists": [{"name": "FooBar"}],
                "album": {"name": "Baz"},
            },
            "track",
            "\x02foobar\x02 by \x02FooBar\x02 from the album \x02Baz\x02",
        ],
    ],
)
def test_format_response(data, item_type, output):
    assert spotify._format_response(data, item_type) == output


@pytest.fixture()
def setup_api(mock_api_keys, mock_requests):
    mock_requests.add(
        "POST",
        "https://accounts.spotify.com/api/token",
        json={"access_token": "foo", "expires_in": 3600},
    )
    importlib.reload(spotify)
    spotify.set_keys()

    yield mock_requests


def test_spotify_url(setup_api):
    match = spotify.http_re.search("open.spotify.com/user/foobar")
    setup_api.add(
        "GET",
        "https://api.spotify.com/v1/users/foobar",
        json={"name": "foo", "followers": {"total": 0},},
    )
    res = spotify.spotify_url(match)
    assert res == "Spotify User: \x02foo\x02, Followers: \x020\x02"


def test_spotify_refresh_token(setup_api):
    spotify.api._token_expires = datetime.min
    match = spotify.http_re.search("open.spotify.com/user/foobar")
    setup_api.add(
        "GET",
        "https://api.spotify.com/v1/users/foobar",
        json={"name": "foo", "followers": {"total": 0},},
    )
    res = spotify.spotify_url(match)
    assert res == "Spotify User: \x02foo\x02, Followers: \x020\x02"


def test_api_active(setup_api):
    assert spotify.api


def test_api_inactive():
    importlib.reload(spotify)

    assert not spotify.api


def test_search_no_results(mock_requests, setup_api):
    mock_requests.add(
        mock_requests.GET,
        "https://api.spotify.com/v1/search",
        json={"users": {"items": []}},
    )

    reply = MagicMock()
    assert spotify._search("foo", "user", reply) is None

    reply.assert_not_called()

    no_user = "Unable to find matching user"

    assert spotify._format_search("foo", "user", reply) == no_user

    reply.assert_not_called()


@pytest.mark.parametrize(
    "func,data,output",
    [
        (
            spotify.spotify,
            {
                "tracks": {
                    "items": [
                        {
                            "name": "foobar",
                            "artists": [{"name": "FooBar"}],
                            "album": {"name": "Baz"},
                            "external_urls": {
                                "spotify": "https://example.com/foo"
                            },
                            "uri": "spotify:track:6rqhFgbbKwnb9MLmUQDhG6",
                            "genres": ["Testing", "Bots", "Foo"],
                        }
                    ]
                }
            },
            "\x02foobar\x02 by \x02FooBar\x02 from the album \x02Baz\x02 - "
            "https://example.com/foo [spotify:track:6rqhFgbbKwnb9MLmUQDhG6]",
        ),
        (
            spotify.spalbum,
            {
                "albums": {
                    "items": [
                        {
                            "uri": "foouri",
                            "external_urls": {"spotify": "foourl"},
                            "name": "foo",
                            "main_artist": {"name": "foobar"},
                        }
                    ]
                }
            },
            "\x02foobar\x02 - \x02foo\x02 - foourl [foouri]",
        ),
        (
            spotify.spartist,
            {
                "artists": {
                    "items": [
                        {
                            "uri": "foouri",
                            "external_urls": {"spotify": "foourl"},
                            "genre_str": "foogenre",
                            "name": "foo",
                            "followers": {"total": 5},
                        }
                    ]
                }
            },
            "\x02foo\x02, followers: \x025\x02, genres: \x02foogenre\x02 - "
            "foourl [foouri]",
        ),
    ],
)
def test_format_search(func, data, output, mock_requests, setup_api):
    mock_requests.add("GET", "https://api.spotify.com/v1/search", json=data)

    reply = MagicMock()

    assert func("foo", reply) == output

    reply.assert_not_called()


def test_missing_format(setup_api):
    setup_api.add(
        "GET",
        "https://api.spotify.com/v1/search?q=foo&offset=0&limit=1&type=bar",
        match_querystring=True,
        json={"baz": {"items": [{"name": "fooname"}]}},
    )
    reply = MagicMock()
    spotify.TYPE_MAP["bar"] = "baz"
    with pytest.raises(
        ValueError, match="Attempt to format unknown Spotify API type: bar"
    ):
        spotify._format_search("foo", "bar", reply)


def test_search_error(setup_api):
    setup_api.add("GET", "https://api.spotify.com/v1/search", status=400)
    reply = MagicMock()
    with pytest.raises(HTTPError):
        spotify._format_search("foo", "artist", reply)

    assert reply.mock_calls == [call("Could not get information: 400")]
