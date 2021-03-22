from json import JSONDecodeError

import pytest
import requests
from requests import HTTPError
from responses import RequestsMock

from cloudbot.bot import bot
from plugins import lastfm


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
    url = "http://ws.audioscrobbler.com/2.0/?format=json&artist=foobar&autocorrect=1&method=artist.getTopTags&api_key=APIKEY"
    mock_requests.add(
        "GET",
        url,
        json={
            "toptags": {},
        },
        match_querystring=True,
    )
    res = lastfm.getartisttags("foobar")
    assert res == "no tags"


class TestGetArtistTags:
    url = "http://ws.audioscrobbler.com/2.0/?format=json&artist=foobar&autocorrect=1&method=artist.getTopTags&api_key=APIKEY"

    def get_tags(self):
        return lastfm.getartisttags("foobar")

    def test_missing_tags(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.url,
            json={
                "toptags": {},
            },
            match_querystring=True,
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
            match_querystring=True,
        )
        res = self.get_tags()
        assert res == "no tags"

    def test_non_existent_artist(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.url,
            json={"error": 6, "message": "Missing artist."},
            match_querystring=True,
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
            match_querystring=True,
        )
        res = self.get_tags()
        assert res == "tag2, tag4, tag5, tag6"


def test_gettracktags(mock_requests, mock_api_keys):
    url = "http://ws.audioscrobbler.com/2.0/?format=json&artist=foobar&autocorrect=1&track=foobaz&method=track.getTopTags&api_key=APIKEY"
    mock_requests.add(
        "GET",
        url,
        json={"toptags": {}},
        match_querystring=True,
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
            "http://ws.audioscrobbler.com/2.0/?format=json&user=bar&limit=10&period=7day&method=user.gettopartists&api_key=APIKEY",
            match_querystring=True,
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
            "http://ws.audioscrobbler.com/2.0/?format=json&user=bar&limit=5&method=user.gettoptracks&api_key=APIKEY",
            match_querystring=True,
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
