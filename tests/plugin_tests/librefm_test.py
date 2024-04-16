from unittest.mock import MagicMock

from responses import RequestsMock
from responses.matchers import query_param_matcher

from cloudbot.event import CommandEvent
from plugins import librefm
from tests.util import wrap_hook_response
from tests.util.mock_db import MockDB


def test_get_account(mock_db, mock_requests):
    librefm.table.create(mock_db.engine)
    mock_db.add_row(librefm.table, nick="foo", acc="bar")
    librefm.load_cache(mock_db.session())

    assert librefm.get_account("foo") == "bar"
    assert librefm.get_account("FOO") == "bar"
    assert librefm.get_account("foo1") is None
    assert librefm.get_account("foo1") is None


def test_getartisttags(mock_requests):
    url = "https://libre.fm/2.0/"
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
                    "method": "artist.getTopTags",
                }
            )
        ],
    )
    res = librefm.getartisttags("foobar")
    assert res == "no tags"


class TestGetArtistTags:
    url = "https://libre.fm/2.0/"

    def get_params(self):
        return {
            "format": "json",
            "artist": "foobar",
            "method": "artist.getTopTags",
        }

    def get_tags(self):
        return librefm.getartisttags("foobar")

    def test_missing_tags(self, mock_requests):
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

    def test_no_tags(self, mock_requests):
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

    def test_non_existent_artist(self, mock_requests):
        mock_requests.add(
            "GET",
            self.url,
            json={"error": 6, "message": "Missing artist."},
            match=[query_param_matcher(self.get_params())],
        )
        res = self.get_tags()
        assert res == "no tags"

    def test_tags(self, mock_requests):
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
        assert res == "foobar, tag2, seen live, tag4"


class TestTopArtists:
    def test_topweek_self(self, mock_requests, mock_db):
        librefm.table.create(mock_db.engine)
        mock_db.add_row(librefm.table, nick="foo", acc="bar")
        librefm.load_cache(mock_db.session())

        mock_requests.add(
            "GET",
            "https://libre.fm/2.0/",
            match=[
                query_param_matcher(
                    {
                        "format": "json",
                        "user": "bar",
                        "limit": "10",
                        "period": "7day",
                        "method": "user.gettopartists",
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

        out = librefm.topweek("", "foo")

        assert out == "bar's favorite artists: foo [5] bar [2] "


class TestTopTrack:
    def test_toptrack_self(self, mock_requests, mock_db):
        librefm.table.create(mock_db.engine)
        mock_db.add_row(librefm.table, nick="foo", acc="bar")
        librefm.load_cache(mock_db.session())

        mock_requests.add(
            "GET",
            "https://libre.fm/2.0/",
            match=[
                query_param_matcher(
                    {
                        "format": "json",
                        "user": "bar",
                        "limit": "5",
                        "method": "user.gettoptracks",
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

        out = librefm.toptrack("", "foo")

        expected = "bar's favorite songs: some song by some artist listened to 10 times. "

        assert out == expected


def test_save_account(
    mock_db: MockDB,
    mock_bot,
    mock_requests: RequestsMock,
    mock_bot_factory,
    freeze_time,
):
    librefm.table.create(mock_db.engine)
    librefm.load_cache(mock_db.session())
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
        "https://libre.fm/2.0/",
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "user": "myaccount",
                    "limit": "1",
                    "method": "user.getrecenttracks",
                }
            )
        ],
        json={
            "recenttracks": {
                "track": {
                    "name": track_name,
                    "album": {"#text": "foo"},
                    "artist": {"#text": artist_name},
                    "date": {"uts": 156432453},
                    "url": "https://example.com",
                }
            }
        },
    )

    mock_requests.add(
        "GET",
        "https://libre.fm/2.0/",
        json={"toptags": {"tag": [{"name": "thing"}]}},
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "artist": artist_name,
                    "method": "artist.getTopTags",
                }
            )
        ],
    )

    results = wrap_hook_response(librefm.librefm, event)
    assert results == [
        (
            "return",
            'myaccount last listened to "some track" by \x02bar\x0f from the album \x02foo\x0f https://example.com (thing) (44 years and 8 months ago)',
        ),
    ]
    assert mock_db.get_data(librefm.table) == [
        ("foo", "myaccount"),
    ]


def test_update_account(
    mock_db: MockDB,
    mock_bot,
    mock_requests: RequestsMock,
    mock_bot_factory,
    freeze_time,
):
    librefm.table.create(mock_db.engine)
    mock_db.add_row(librefm.table, nick="foo", acc="oldaccount")
    librefm.load_cache(mock_db.session())
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
        "https://libre.fm/2.0/",
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "user": "myaccount",
                    "limit": "1",
                    "method": "user.getrecenttracks",
                }
            )
        ],
        json={
            "recenttracks": {
                "track": {
                    "name": track_name,
                    "album": {"#text": "foo"},
                    "artist": {"#text": artist_name},
                    "date": {"uts": 156432453},
                    "url": "https://example.com",
                }
            }
        },
    )

    mock_requests.add(
        "GET",
        "https://libre.fm/2.0/",
        json={"toptags": {"tag": [{"name": "thing"}]}},
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "artist": artist_name,
                    "method": "artist.getTopTags",
                }
            )
        ],
    )

    results = wrap_hook_response(librefm.librefm, event)
    assert results == [
        (
            "return",
            'myaccount last listened to "some track" by \x02bar\x0f from the album \x02foo\x0f https://example.com (thing) (44 years and 8 months ago)',
        ),
    ]

    assert mock_db.get_data(librefm.table) == [
        ("foo", "myaccount"),
    ]
