from json import JSONDecodeError
from unittest.mock import MagicMock

import pytest
import requests
from requests import HTTPError
from responses import RequestsMock
from responses.matchers import query_param_matcher

from cloudbot.bot import bot
from cloudbot.event import CommandEvent
from plugins import lastfm
from tests.util import wrap_hook_response
from tests.util.mock_db import MockDB


def test_get_account(mock_db, mock_requests):
    lastfm.table.create(mock_db.engine)
    mock_db.add_row(lastfm.table, nick="foo", acc="bar")
    lastfm.load_cache(mock_db.session())

    assert lastfm.get_account("foo", "baz") == "bar"
    assert lastfm.get_account("FOO", "baz") == "bar"
    assert lastfm.get_account("foo1", "baz") == "baz"
    assert lastfm.get_account("foo1", "baa") == "baa"


def test_api(mock_bot_factory, unset_bot, event_loop):
    bot.set(
        mock_bot_factory(
            loop=event_loop, config={"api_keys": {"lastfm": "hunter20"}}
        )
    )

    with RequestsMock() as reqs:
        with pytest.raises(requests.ConnectionError):
            lastfm.api_request("track.getTopTags")

        reqs.add(
            "GET",
            "http://ws.audioscrobbler.com/2.0/",
            json={"data": "thing"},
        )

        res, _ = lastfm.api_request("track.getTopTags")

        assert res["data"] == "thing"

    with RequestsMock() as reqs:
        reqs.add(
            "GET", "http://ws.audioscrobbler.com/2.0/", body="<html></html>"
        )

        with pytest.raises(JSONDecodeError):
            lastfm.api_request("track.getTopTags")

    with RequestsMock() as reqs:
        reqs.add(
            "GET",
            "http://ws.audioscrobbler.com/2.0/",
            body="<html></html>",
            status=403,
        )

        with pytest.raises(HTTPError):
            lastfm.api_request("track.getTopTags")


def test_api_error_message(mock_requests, mock_api_keys):
    mock_requests.add(
        "GET",
        "http://ws.audioscrobbler.com/2.0/",
        json={
            "error": 10,
            "message": "Invalid API Key",
        },
    )

    _, error = lastfm.api_request("track.getTopTags")

    assert error == "Error: Invalid API Key."


def test_getartisttags(mock_requests, mock_api_keys):
    url = "http://ws.audioscrobbler.com/2.0/"
    mock_requests.add(
        "GET",
        url,
        json={
            "toptags": {},
        },
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "artist": "foobar",
                    "autocorrect": 1,
                    "method": "artist.getTopTags",
                    "api_key": "APIKEY",
                }
            )
        ],
    )
    res = lastfm.getartisttags("foobar")
    assert res == "no tags"


class TestGetArtistTags:
    url = "http://ws.audioscrobbler.com/2.0/"

    def get_params(self):
        return {
            "format": "json",
            "artist": "foobar",
            "autocorrect": "1",
            "method": "artist.getTopTags",
            "api_key": "APIKEY",
        }

    def get_tags(self):
        return lastfm.getartisttags("foobar")

    def test_missing_tags(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.url,
            json={
                "toptags": {},
            },
            match=[query_param_matcher(self.get_params())],
        )
        res = self.get_tags()
        assert res == "no tags"

    def test_no_tags(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.url,
            json={
                "toptags": {"tags": []},
            },
            match=[query_param_matcher(self.get_params())],
        )
        res = self.get_tags()
        assert res == "no tags"

    def test_non_existent_artist(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.url,
            json={"error": 6, "message": "Missing artist."},
            match=[query_param_matcher(self.get_params())],
        )
        res = self.get_tags()
        assert res == "no tags"

    def test_tags(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.url,
            json={
                "toptags": {
                    "tag": [
                        {"name": name}
                        for name in [
                            "foobar",
                            "tag2",
                            "seen live",
                            "tag4",
                            "tag5",
                            "tag6",
                            "tag7",
                        ]
                    ]
                },
            },
            match=[query_param_matcher(self.get_params())],
        )
        res = self.get_tags()
        assert res == "tag2, tag4, tag5, tag6"


def test_gettracktags(mock_requests, mock_api_keys):
    url = "http://ws.audioscrobbler.com/2.0/"
    mock_requests.add(
        "GET",
        url,
        json={"toptags": {}},
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "artist": "foobar",
                    "autocorrect": 1,
                    "track": "foobaz",
                    "method": "track.getTopTags",
                    "api_key": "APIKEY",
                }
            )
        ],
    )
    res = lastfm.gettracktags("foobar", "foobaz")
    assert res == "no tags"


class TestCheckKeyAndUser:
    def test_text(self, mock_api_keys, mock_requests, mock_db):
        lastfm.table.create(mock_db.engine)
        mock_db.add_row(lastfm.table, nick="foo", acc="bar")
        lastfm.load_cache(mock_db.session())

        res, err = lastfm.check_key_and_user("foo", "baz")
        assert err is None
        assert res == "baz"

    def test_db_lookup(self, mock_api_keys, mock_requests, mock_db):
        lastfm.table.create(mock_db.engine)
        mock_db.add_row(lastfm.table, nick="foo", acc="bar")
        lastfm.load_cache(mock_db.session())

        res, err = lastfm.check_key_and_user("foo", "")
        assert err is None
        assert res == "bar"

    def test_missing_user(self, mock_api_keys, mock_requests, mock_db):
        lastfm.table.create(mock_db.engine)
        mock_db.add_row(lastfm.table, nick="foo", acc="bar")
        lastfm.load_cache(mock_db.session())

        res, err = lastfm.check_key_and_user("foo1", "")
        assert res is None
        expected = "No last.fm username specified and no last.fm username is set in the database."
        assert err == expected

    def test_no_key(self, mock_api_keys, mock_requests, mock_db):
        bot.config.get_api_key.return_value = None  # type: ignore
        res, err = lastfm.check_key_and_user("foo", "baz")
        assert res is None
        assert err == "Error: No API key set."


class TestTopArtists:
    def test_topweek_self(self, mock_api_keys, mock_requests, mock_db):
        lastfm.table.create(mock_db.engine)
        mock_db.add_row(lastfm.table, nick="foo", acc="bar")
        lastfm.load_cache(mock_db.session())

        mock_requests.add(
            "GET",
            "http://ws.audioscrobbler.com/2.0/",
            match=[
                query_param_matcher(
                    {
                        "format": "json",
                        "user": "bar",
                        "limit": "10",
                        "period": "7day",
                        "method": "user.gettopartists",
                        "api_key": "APIKEY",
                    }
                )
            ],
            json={
                "topartists": {
                    "artist": [
                        {"name": "foo", "playcount": 5},
                        {"name": "bar", "playcount": 2},
                    ]
                }
            },
        )

        out = lastfm.topweek("", "foo")

        assert out == "b\u200bar's favorite artists: foo [5] bar [2] "


class TestTopTrack:
    def test_toptrack_self(self, mock_api_keys, mock_requests, mock_db):
        lastfm.table.create(mock_db.engine)
        mock_db.add_row(lastfm.table, nick="foo", acc="bar")
        lastfm.load_cache(mock_db.session())

        mock_requests.add(
            "GET",
            "http://ws.audioscrobbler.com/2.0/",
            match=[
                query_param_matcher(
                    {
                        "format": "json",
                        "user": "bar",
                        "limit": "5",
                        "method": "user.gettoptracks",
                        "api_key": "APIKEY",
                    }
                )
            ],
            json={
                "toptracks": {
                    "track": [
                        {
                            "name": "some song",
                            "artist": {"name": "some artist"},
                            "playcount": 10,
                        }
                    ]
                }
            },
        )

        out = lastfm.toptrack("", "foo")

        expected = "b\u200bar's favorite songs: some song by some artist listened to 10 times. "

        assert out == expected


def test_save_account(
    mock_db: MockDB, mock_requests: RequestsMock, mock_bot_factory, freeze_time
):
    lastfm.table.create(mock_db.engine)
    lastfm.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={"api_keys": {"lastfm": "APIKEY"}})
    hook = MagicMock()
    event = CommandEvent(
        bot=mock_bot,
        hook=hook,
        text="myaccount",
        triggered_command="np",
        cmd_prefix=".",
        nick="foo",
        conn=MagicMock(),
    )

    event.db = mock_db.session()

    track_name = "some track"
    artist_name = "bar"
    mock_requests.add(
        "GET",
        "http://ws.audioscrobbler.com/2.0/",
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "user": "myaccount",
                    "limit": "1",
                    "method": "user.getrecenttracks",
                    "api_key": "APIKEY",
                }
            )
        ],
        json={
            "recenttracks": {
                "track": [
                    {
                        "name": track_name,
                        "album": {"#text": "foo"},
                        "artist": {"#text": artist_name},
                        "date": {"uts": 156432453},
                        "url": "https://example.com",
                    }
                ]
            }
        },
    )

    mock_requests.add(
        "GET",
        "http://ws.audioscrobbler.com/2.0/",
        json={"toptags": {"tag": [{"name": "thing"}]}},
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "artist": artist_name,
                    "autocorrect": "1",
                    "track": track_name,
                    "method": "track.getTopTags",
                    "api_key": "APIKEY",
                }
            )
        ],
    )

    mock_requests.add(
        "GET",
        "http://ws.audioscrobbler.com/2.0/",
        json={"track": {"userplaycount": 3}},
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "artist": artist_name,
                    "track": track_name,
                    "method": "track.getInfo",
                    "api_key": "APIKEY",
                    "username": "myaccount",
                }
            )
        ],
    )

    results = wrap_hook_response(lastfm.lastfm, event)
    assert mock_db.get_data(lastfm.table) == [
        ("foo", "myaccount"),
    ]
    assert results == [
        (
            "return",
            'm\u200byaccount last listened to "some track" by \x02bar\x0f from the album \x02foo\x0f [playcount: 3] https://example.com (thing) (44 years and 8 months ago)',
        ),
    ]


def test_update_account(
    mock_db: MockDB, mock_requests: RequestsMock, mock_bot_factory, freeze_time
):
    lastfm.table.create(mock_db.engine)
    mock_db.add_row(lastfm.table, nick="foo", acc="oldaccount")
    lastfm.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={"api_keys": {"lastfm": "APIKEY"}})
    hook = MagicMock()
    event = CommandEvent(
        bot=mock_bot,
        hook=hook,
        text="myaccount",
        triggered_command="np",
        cmd_prefix=".",
        nick="foo",
        conn=MagicMock(),
    )

    event.db = mock_db.session()

    track_name = "some track"
    artist_name = "bar"
    mock_requests.add(
        "GET",
        "http://ws.audioscrobbler.com/2.0/",
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "user": "myaccount",
                    "limit": "1",
                    "method": "user.getrecenttracks",
                    "api_key": "APIKEY",
                }
            )
        ],
        json={
            "recenttracks": {
                "track": [
                    {
                        "name": track_name,
                        "album": {"#text": "foo"},
                        "artist": {"#text": artist_name},
                        "date": {"uts": 156432453},
                        "url": "https://example.com",
                    }
                ]
            }
        },
    )

    mock_requests.add(
        "GET",
        "http://ws.audioscrobbler.com/2.0/",
        json={"toptags": {"tag": [{"name": "thing"}]}},
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "artist": artist_name,
                    "autocorrect": "1",
                    "track": track_name,
                    "method": "track.getTopTags",
                    "api_key": "APIKEY",
                }
            )
        ],
    )

    mock_requests.add(
        "GET",
        "http://ws.audioscrobbler.com/2.0/",
        json={"track": {"userplaycount": 3}},
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "artist": artist_name,
                    "track": track_name,
                    "method": "track.getInfo",
                    "api_key": "APIKEY",
                    "username": "myaccount",
                }
            )
        ],
    )

    results = wrap_hook_response(lastfm.lastfm, event)
    assert mock_db.get_data(lastfm.table) == [
        ("foo", "myaccount"),
    ]
    assert results == [
        (
            "return",
            'm\u200byaccount last listened to "some track" by \x02bar\x0f from the album \x02foo\x0f [playcount: 3] https://example.com (thing) (44 years and 8 months ago)',
        ),
    ]
