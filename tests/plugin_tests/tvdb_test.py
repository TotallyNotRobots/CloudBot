from abc import ABC, abstractmethod
from typing import List
from unittest.mock import MagicMock

import pytest
import requests

from cloudbot.bot import bot
from cloudbot.event import CommandEvent
from plugins import tvdb
from tests.util import HookResult, wrap_hook_response


@pytest.fixture()
def reset_api():
    try:
        yield
    finally:
        tvdb.api = tvdb.TvdbApi()


@pytest.fixture()
def enable_api():
    tvdb.api.set_token("foobar")


def test_holder_of_optional():
    holder: tvdb.Holder[int] = tvdb.Holder()
    with pytest.raises(tvdb.MissingItem):
        holder.get()

    holder.set(1)
    assert holder.get() == 1

    holder2 = tvdb.Holder.of_optional(None)
    assert not holder2.exists()

    holder = tvdb.Holder.of_optional(1)
    assert holder.exists()


def test_token(mock_requests, reset_api, mock_api_keys):
    mock_requests.add(
        "POST", "https://api.thetvdb.com/login", json={"token": "foobar3"}
    )
    tvdb.api.refresh_token(MagicMock(config=bot.config))
    assert tvdb.api.jwt_token == "foobar3"


def test_refresh(mock_requests, reset_api, mock_api_keys, enable_api):
    mock_requests.add(
        "GET",
        "https://api.thetvdb.com/refresh_token",
        json={"token": "foobar1"},
    )
    tvdb.refresh(MagicMock(config=bot.config))
    assert tvdb.api.jwt_token == "foobar1"


def test_refresh_expired(mock_requests, reset_api, mock_api_keys, enable_api):
    mock_requests.add(
        "GET", "https://api.thetvdb.com/refresh_token", status=401
    )
    mock_requests.add(
        "POST", "https://api.thetvdb.com/login", json={"token": "foobar2"}
    )
    tvdb.api.refresh_token(MagicMock(config=bot.config))
    assert tvdb.api.jwt_token == "foobar2"


def test_refresh_other_error(
    mock_requests, reset_api, mock_api_keys, enable_api
):
    mock_requests.add(
        "GET", "https://api.thetvdb.com/refresh_token", status=502
    )
    with pytest.raises(requests.HTTPError):
        tvdb.api.refresh_token(MagicMock(config=bot.config))


def generate_pages(mock_requests, url, count=5, per_page=5):
    for i in range(1, count + 1):
        links = {
            "previous": i - 1,
            "next": i + 1,
            "last": count,
            "first": 1,
        }

        if links["previous"] <= 0:
            links["previous"] = None

        if links["next"] > count:
            links["next"] = None

        mock_requests.add(
            "GET",
            url + "?page={}".format(i),
            match_querystring=True,
            json={
                "data": [{"id": "{}.{}".format(i, j)} for j in range(per_page)],
                "links": links,
            },
        )


def test_paging(mock_requests, reset_api, enable_api):
    generate_pages(mock_requests, "https://api.thetvdb.com/series/42/episodes")
    eps = list(tvdb.api.get_episodes("42"))
    assert eps == [
        {"id": "5.4"},
        {"id": "5.3"},
        {"id": "5.2"},
        {"id": "5.1"},
        {"id": "5.0"},
        {"id": "4.4"},
        {"id": "4.3"},
        {"id": "4.2"},
        {"id": "4.1"},
        {"id": "4.0"},
        {"id": "3.4"},
        {"id": "3.3"},
        {"id": "3.2"},
        {"id": "3.1"},
        {"id": "3.0"},
        {"id": "2.4"},
        {"id": "2.3"},
        {"id": "2.2"},
        {"id": "2.1"},
        {"id": "2.0"},
        {"id": "1.4"},
        {"id": "1.3"},
        {"id": "1.2"},
        {"id": "1.1"},
        {"id": "1.0"},
    ]


def test_paging_reverse(mock_requests, reset_api, enable_api):
    generate_pages(mock_requests, "https://api.thetvdb.com/series/42/episodes")
    eps = list(tvdb.api.get_episodes("42", reverse=False))
    assert eps == [
        {"id": "1.0"},
        {"id": "1.1"},
        {"id": "1.2"},
        {"id": "1.3"},
        {"id": "1.4"},
        {"id": "2.0"},
        {"id": "2.1"},
        {"id": "2.2"},
        {"id": "2.3"},
        {"id": "2.4"},
        {"id": "3.0"},
        {"id": "3.1"},
        {"id": "3.2"},
        {"id": "3.3"},
        {"id": "3.4"},
        {"id": "4.0"},
        {"id": "4.1"},
        {"id": "4.2"},
        {"id": "4.3"},
        {"id": "4.4"},
        {"id": "5.0"},
        {"id": "5.1"},
        {"id": "5.2"},
        {"id": "5.3"},
        {"id": "5.4"},
    ]


@pytest.mark.usefixtures("mock_requests", "reset_api", "freeze_time")
class _Base(ABC):
    @abstractmethod
    def get_func(self):
        raise NotImplementedError

    def call(self, text: str, results=None):
        event = CommandEvent(
            cmd_prefix=".",
            hook=MagicMock(),
            text=text,
            triggered_command="tv",
            conn=MagicMock(),
            channel="#foo",
            nick="nick",
        )
        return wrap_hook_response(self.get_func(), event, results=results)

    def test_api_off(self):
        res = self.call("Foo")
        assert res == [("return", "TVDB API not enabled.")]

    def test_404(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=404,
        )

        res = self.call("Foo")
        assert res == [("return", "Unable to find series")]

    def test_other_errors(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=502,
        )

        results: List[HookResult] = []
        with pytest.raises(requests.HTTPError):
            self.call("Foo", results=results)

        assert results == [
            ("message", ("#foo", "(nick) Failed to contact thetvdb.com"))
        ]

    @abstractmethod
    def get_no_ep_msg(self):
        raise NotImplementedError

    @abstractmethod
    def shows_old_eps(self):
        raise NotImplementedError

    @abstractmethod
    def shows_new_eps(self):
        raise NotImplementedError

    def test_no_episodes(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=200,
            json={
                "data": [
                    {
                        "id": "5",
                        "status": tvdb.Status.CONTINUING.value,
                        "seriesName": "Foo: Bar",
                    }
                ]
            },
        )

        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/series/5/episodes?page=1",
            match_querystring=True,
            json={
                "data": [],
            },
        )

        res = self.call("Foo")
        assert res == self.get_no_ep_msg()

    def test_no_episodes_404(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=200,
            json={
                "data": [
                    {
                        "id": "5",
                        "status": tvdb.Status.CONTINUING.value,
                        "seriesName": "Foo: Bar",
                    }
                ]
            },
        )

        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/series/5/episodes?page=1",
            match_querystring=True,
            json={
                "data": [],
            },
            status=404,
        )

        results = self.call("Foo")

        assert results == self.get_no_ep_msg()

    def test_ep_other_error(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=200,
            json={
                "data": [
                    {
                        "id": "5",
                        "status": tvdb.Status.CONTINUING.value,
                        "seriesName": "Foo: Bar",
                    }
                ]
            },
        )

        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/series/5/episodes?page=1",
            match_querystring=True,
            json={},
            status=503,
        )

        results: List[HookResult] = []
        with pytest.raises(requests.HTTPError):
            self.call("Foo", results=results)

        assert results == [
            ("message", ("#foo", "(nick) Failed to contact thetvdb.com"))
        ]

    def test_only_old_eps(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=200,
            json={
                "data": [
                    {
                        "id": "5",
                        "status": tvdb.Status.CONTINUING.value,
                        "seriesName": "Foo: Bar",
                    }
                ]
            },
        )

        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/series/5/episodes?page=1",
            match_querystring=True,
            json={
                "data": [
                    {
                        "airedEpisodeNumber": 1,
                        "airedSeason": 1,
                        "firstAired": "2017-02-02",
                    }
                ],
            },
        )

        res = self.call("Foo")
        if self.shows_old_eps():
            assert res == [
                (
                    "return",
                    "The last episode of Foo: Bar aired 2017-02-02 (S01E01).",
                )
            ]
        else:
            assert res == [
                ("return", "There are no new episodes scheduled for Foo: Bar.")
            ]

    def test_only_new_eps(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=200,
            json={
                "data": [
                    {
                        "id": "5",
                        "status": tvdb.Status.CONTINUING.value,
                        "seriesName": "Foo: Bar",
                    }
                ]
            },
        )

        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/series/5/episodes?page=1",
            match_querystring=True,
            json={
                "data": [
                    {
                        "airedEpisodeNumber": 1,
                        "airedSeason": 1,
                        "firstAired": "2020-02-02",
                    }
                ],
            },
        )

        res = self.call("Foo")
        if self.shows_new_eps():
            assert res == [
                (
                    "return",
                    "The next episode of Foo: Bar airs 2020-02-02 (S01E01)",
                )
            ]
        else:
            assert res == [
                (
                    "return",
                    "There are no previously aired episodes for Foo: Bar.",
                )
            ]

    def test_only_new_eps_tba(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=200,
            json={
                "data": [
                    {
                        "id": "5",
                        "status": tvdb.Status.CONTINUING.value,
                        "seriesName": "Foo: Bar",
                    }
                ]
            },
        )

        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/series/5/episodes?page=1",
            match_querystring=True,
            json={
                "data": [
                    {
                        "airedEpisodeNumber": 0,
                        "airedSeason": 1,
                        "firstAired": "2019-08-22",
                    },
                    {
                        "airedEpisodeNumber": 1,
                        "airedSeason": 1,
                        "firstAired": "2020-02-02",
                    },
                    {
                        "airedEpisodeNumber": 2,
                        "airedSeason": 1,
                        "firstAired": "2020-02-05",
                        "episodeName": "TBA",
                    },
                    {
                        "airedEpisodeNumber": 3,
                        "airedSeason": 1,
                        "firstAired": "2020-02-05",
                        "episodeName": "baz",
                    },
                    {
                        "airedEpisodeNumber": 4,
                        "airedSeason": 1,
                    },
                ],
            },
        )

        res = self.call("Foo")
        if self.shows_new_eps():
            assert res == [
                (
                    "return",
                    "The next episodes of Foo: Bar: Today (S01E00), 2020-02-02 (S01E01), 2020-02-05 (S01E02), 2020-02-05 (S01E03 - baz), TBA (S01E04)",
                )
            ]
        else:
            assert res == [
                (
                    "return",
                    "There are no previously aired episodes for Foo: Bar.",
                )
            ]

    def test_series_ended(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=200,
            json={
                "data": [
                    {
                        "id": "5",
                        "status": tvdb.Status.ENDED.value,
                        "seriesName": "Foo: Bar",
                    }
                ]
            },
        )

        if self.shows_old_eps():
            mock_requests.add(
                "GET",
                "https://api.thetvdb.com/series/5/episodes?page=1",
                match_querystring=True,
                json={
                    "data": [
                        {
                            "firstAired": "2018-01-01",
                            "airedEpisodeNumber": 1,
                            "airedSeason": 1,
                        }
                    ],
                },
            )

        res = self.call("Foo")
        if self.shows_new_eps():
            assert res == [("return", "Foo: Bar has ended.")]
        else:
            assert res == [
                (
                    "return",
                    "Foo: Bar ended. The last episode aired 2018-01-01 (S01E01).",
                )
            ]

    def test_only_new_eps_tba_no_name(self, mock_requests, enable_api):
        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/search/series?name=Foo",
            match_querystring=True,
            status=200,
            json={
                "data": [
                    {
                        "id": "5",
                        "status": tvdb.Status.CONTINUING.value,
                        "seriesName": "TBA",
                    }
                ]
            },
        )

        mock_requests.add(
            "GET",
            "https://api.thetvdb.com/series/5/episodes?page=1",
            match_querystring=True,
            json={
                "data": [
                    {
                        "airedEpisodeNumber": 1,
                        "airedSeason": 1,
                        "firstAired": "2020-02-02",
                    },
                    {
                        "airedEpisodeNumber": 2,
                        "airedSeason": 1,
                    },
                ],
            },
        )

        res = self.call("Foo")
        if self.shows_new_eps():
            assert res == [
                (
                    "return",
                    "The next episodes of TBA: 2020-02-02 (S01E01), TBA (S01E02)",
                )
            ]
        else:
            assert res == [
                ("return", "There are no previously aired episodes for TBA.")
            ]


class TestNext(_Base):
    def shows_old_eps(self):
        return False

    def shows_new_eps(self):
        return True

    def get_no_ep_msg(self):
        return [("return", "There are no new episodes scheduled for Foo: Bar.")]

    def get_func(self):
        return tvdb.tv_next


class TestPrev(_Base):
    def shows_old_eps(self):
        return True

    def shows_new_eps(self):
        return False

    def get_no_ep_msg(self):
        return [
            ("return", "There are no previously aired episodes for Foo: Bar.")
        ]

    def get_func(self):
        return tvdb.tv_last
