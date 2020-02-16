import importlib

import pytest
from unittest.mock import MagicMock

from tests.util.mock_bot import MockBot


@pytest.mark.parametrize(
    "text,item_type,item_id", [("open.spotify.com/user/foobar", "user", "foobar")]
)
def test_http_re(text, item_type, item_id):
    from plugins.spotify import http_re

    match = http_re.search(text)
    assert match and match.group(2) == item_type and match.group(3) == item_id


@pytest.mark.parametrize(
    "text,item_type,item_id", [("spotify:user:foobar", "user", "foobar")]
)
def test_spotify_re(text, item_type, item_id):
    from plugins.spotify import spotify_re

    match = spotify_re.search(text)
    assert match and match.group(2) == item_type and match.group(3) == item_id


@pytest.mark.parametrize(
    "data,item_type,output",
    [
        [
            {
                "display_name": "linuxdaemon",
                "external_urls": {"spotify": "https://open.spotify.com/user/7777"},
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
    from plugins.spotify import _format_response

    assert _format_response(data, item_type) == output


@pytest.fixture()
def setup_api(unset_bot, mock_requests):
    from cloudbot.bot import bot

    bot.set(
        MockBot(
            {
                "api_keys": {
                    "spotify_client_id": "APIKEY",
                    "spotify_client_secret": "APIKEY",
                }
            }
        )
    )
    mock_requests.add(
        "POST",
        "https://accounts.spotify.com/api/token",
        json={"access_token": "foo", "expires_in": 3600},
    )
    from plugins import spotify
    importlib.reload(spotify)
    spotify.set_keys()

    yield


def test_api_active(setup_api):
    from plugins import spotify

    assert spotify.api


def test_api_inactive():
    from plugins import spotify
    importlib.reload(spotify)

    assert not spotify.api


def test_search_no_results(mock_requests, setup_api):
    from plugins import spotify

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
    "data,output",
    [
        [
            {
                "tracks": {
                    "items": [
                        {
                            "name": "foobar",
                            "artists": [{"name": "FooBar"}],
                            "album": {"name": "Baz"},
                            "external_urls": {"spotify": "https://example.com/foo"},
                            "uri": "spotify:track:6rqhFgbbKwnb9MLmUQDhG6",
                            "genres": ["Testing", "Bots", "Foo"],
                        }
                    ]
                }
            },
            "\x02foobar\x02 by \x02FooBar\x02 from the album \x02Baz\x02 - "
            "https://example.com/foo [spotify:track:6rqhFgbbKwnb9MLmUQDhG6]",
        ]
    ],
)
def test_format_search_track(data, output, mock_requests, setup_api):
    from plugins import spotify
    mock_requests.add("GET", "https://api.spotify.com/v1/search", json=data)

    reply = MagicMock()

    assert spotify.spotify("foo", reply) == output

    reply.assert_not_called()
