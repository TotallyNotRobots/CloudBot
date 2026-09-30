"""listenbrainz plugin tests."""
from __future__ import annotations

from json import JSONDecodeError
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import requests
from responses import RequestsMock
from responses.matchers import query_param_matcher

from cloudbot.event import CommandEvent
from plugins import listenbrainz
from tests.util import wrap_hook_response

if TYPE_CHECKING:
    from tests.util.mock_db import MockDB


API_URL = "https://api.listenbrainz.org/1"


def test_get_account(mock_db, mock_requests) -> None:
    listenbrainz.table.create(mock_db.engine)
    mock_db.add_row(listenbrainz.table, nick="foo", acc="bar")
    listenbrainz.load_cache(mock_db.session())

    assert listenbrainz.get_account("foo", "baz") == "bar"
    assert listenbrainz.get_account("FOO", "baz") == "bar"
    assert listenbrainz.get_account("foo1", "baz") == "baz"
    assert listenbrainz.get_account("foo1", "baa") == "baa"


@pytest.mark.asyncio
async def test_api(mock_bot_factory, unset_bot) -> None:
    _ = mock_bot_factory(config={})

    with RequestsMock() as reqs:
        with pytest.raises(requests.ConnectionError):
            listenbrainz.api_request("/user/foobar/listens")

        reqs.add(
            "GET",
            f"{API_URL}/user/foobar/listens",
            json={"payload": {"listens": []}},
        )
        res, err = listenbrainz.api_request("/user/foobar/listens")
        assert err is None
        assert res == {"payload": {"listens": []}}

    with RequestsMock() as reqs:
        reqs.add(
            "GET",
            f"{API_URL}/user/foobar/listens",
            body="<html></html>",
        )
        with pytest.raises(JSONDecodeError):
            listenbrainz.api_request("/user/foobar/listens")

    with RequestsMock() as reqs:
        reqs.add(
            "GET",
            f"{API_URL}/user/foobar/listens",
            body="<html></html>",
            status=403,
        )
        with pytest.raises(requests.HTTPError):
            listenbrainz.api_request("/user/foobar/listens")


def test_api_error_message(mock_requests) -> None:
    mock_requests.add(
        "GET",
        f"{API_URL}/user/foobar/listens",
        json={"code": 404, "error": "Cannot find user: foobar"},
    )
    _, err = listenbrainz.api_request("/user/foobar/listens")
    assert err == "ListenBrainz error: Cannot find user: foobar."


def _make_event(bot, text, nick="foo"):
    hook = MagicMock()
    event = CommandEvent(
        bot=bot,
        hook=hook,
        text=text,
        triggered_command="listenbrainz",
        cmd_prefix=".",
        nick=nick,
        conn=MagicMock(),
    )
    return event


def _add_now_playing_playback(reqs, user, playing_now, listened_at):
    reqs.add(
        "GET",
        f"{API_URL}/user/{user}/playing-now",
        match=[query_param_matcher({"limit": "1"})],
        json={
            "payload": {
                "count": 1,
                "listens": [
                    {
                        "playing_now": playing_now,
                        "listened_at": listened_at,
                        "track_metadata": {
                            "artist_name": "some artist",
                            "release_name": "some album",
                            "track_name": "some track",
                        },
                        "user_name": user,
                    }
                ],
                "playing_now": playing_now,
                "user_id": user,
            }
        },
    )


@pytest.mark.asyncio
async def test_listenbrainz_now_playing(
    mock_db: MockDB,
    mock_bot_factory,
    mock_requests: RequestsMock,
    freeze_time,
) -> None:
    listenbrainz.table.create(mock_db.engine)
    listenbrainz.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={})
    _add_now_playing_playback(mock_requests, "mockuser", True, 156432453)

    event = _make_event(mock_bot, "mockuser")
    event.db = mock_db.session()

    results = wrap_hook_response(listenbrainz.listenbrainz, event)
    assert results == [
        (
            "return",
            (
                "m\u200bockuser is listening to "
                "\"some track\" by \x02some artist\x0f "
                "from the album \x02some album\x0f."
            ),
        )
    ]
    assert mock_db.get_data(listenbrainz.table) == [
        ("foo", "mockuser"),
    ]


@pytest.mark.asyncio
async def test_listenbrainz_last_listened(
    mock_db: MockDB,
    mock_bot_factory,
    mock_requests: RequestsMock,
    freeze_time,
) -> None:
    listenbrainz.table.create(mock_db.engine)
    listenbrainz.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={})
    _add_now_playing_playback(mock_requests, "mockuser", False, 156432453)
    mock_requests.add(
        "GET",
        f"{API_URL}/user/mockuser/listens",
        match=[query_param_matcher({"limit": "1"})],
        json={
            "payload": {
                "count": 1,
                "listens": [
                    {
                        "listened_at": 156432453,
                        "track_metadata": {
                            "artist_name": "some artist",
                            "release_name": "some album",
                            "track_name": "some track",
                        },
                        "user_name": "mockuser",
                    }
                ],
                "user_id": "mockuser",
            }
        },
    )

    event = _make_event(mock_bot, "mockuser")
    event.db = mock_db.session()

    results = wrap_hook_response(listenbrainz.listenbrainz, event)
    assert results == [
        (
            "return",
            (
                "m\u200bockuser last listened to "
                "\"some track\" by \x02some artist\x0f "
                "from the album \x02some album\x0f "
                "(44 years and 8 months ago)"
            ),
        )
    ]
    assert mock_db.get_data(listenbrainz.table) == [
        ("foo", "mockuser"),
    ]


@pytest.mark.asyncio
async def test_listenbrainz_stale_now_playing(
    mock_db: MockDB,
    mock_bot_factory,
    mock_requests: RequestsMock,
    freeze_time,
) -> None:
    # LB can report playing_now=true with an empty listens array (e.g. a
    # now-playing state with no event details); that must fall back to the
    # history endpoint instead of claiming there are no recent tracks.
    listenbrainz.table.create(mock_db.engine)
    listenbrainz.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={})
    mock_requests.add(
        "GET",
        f"{API_URL}/user/mockuser/playing-now",
        match=[query_param_matcher({"limit": "1"})],
        json={"payload": {"count": 0, "listens": [], "playing_now": True, "user_id": "mockuser"}},
    )
    mock_requests.add(
        "GET",
        f"{API_URL}/user/mockuser/listens",
        match=[query_param_matcher({"limit": "1"})],
        json={
            "payload": {
                "count": 1,
                "listens": [
                    {
                        "listened_at": 156432453,
                        "track_metadata": {
                            "artist_name": "some artist",
                            "release_name": "some album",
                            "track_name": "some track",
                        },
                        "user_name": "mockuser",
                    }
                ],
                "user_id": "mockuser",
            }
        },
    )

    event = _make_event(mock_bot, "mockuser")
    event.db = mock_db.session()

    results = wrap_hook_response(listenbrainz.listenbrainz, event)
    assert results == [
        (
            "return",
            (
                "m\u200bockuser last listened to "
                "\"some track\" by \x02some artist\x0f "
                "from the album \x02some album\x0f "
                "(44 years and 8 months ago)"
            ),
        )
    ]
    assert mock_db.get_data(listenbrainz.table) == [
        ("foo", "mockuser"),
    ]


@pytest.mark.asyncio
async def test_listenbrainz_update_account(
    mock_db: MockDB,
    mock_bot_factory,
    mock_requests: RequestsMock,
    freeze_time,
) -> None:
    listenbrainz.table.create(mock_db.engine)
    mock_db.add_row(listenbrainz.table, nick="foo", acc="oldaccount")
    listenbrainz.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={})
    _add_now_playing_playback(mock_requests, "mockuser", True, 156432453)

    event = _make_event(mock_bot, "mockuser")
    event.db = mock_db.session()

    results = wrap_hook_response(listenbrainz.listenbrainz, event)
    assert results == [
        (
            "return",
            (
                "m\u200bockuser is listening to "
                "\"some track\" by \x02some artist\x0f "
                "from the album \x02some album\x0f."
            ),
        )
    ]
    assert mock_db.get_data(listenbrainz.table) == [
        ("foo", "mockuser"),
    ]


@pytest.mark.asyncio
async def test_listenbrainz_no_recent_tracks(
    mock_db: MockDB,
    mock_bot_factory,
    mock_requests: RequestsMock,
    freeze_time,
) -> None:
    listenbrainz.table.create(mock_db.engine)
    listenbrainz.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={})
    mock_requests.add(
        "GET",
        f"{API_URL}/user/mockuser/playing-now",
        match=[query_param_matcher({"limit": "1"})],
        json={"payload": {"count": 0, "listens": [], "playing_now": False, "user_id": "mockuser"}},
    )
    mock_requests.add(
        "GET",
        f"{API_URL}/user/mockuser/listens",
        match=[query_param_matcher({"limit": "1"})],
        json={"payload": {"count": 0, "listens": [], "user_id": "mockuser"}},
    )

    event = _make_event(mock_bot, "mockuser")
    event.db = mock_db.session()

    results = wrap_hook_response(listenbrainz.listenbrainz, event)
    assert results == [
        (
            "return",
            "No recent tracks for user \"m\u200bockuser\" found.",
        )
    ]
    assert mock_db.get_data(listenbrainz.table) == []


@pytest.mark.asyncio
async def test_listenbrainz_unknown_user(
    mock_db: MockDB,
    mock_bot_factory,
    mock_requests: RequestsMock,
    freeze_time,
) -> None:
    listenbrainz.table.create(mock_db.engine)
    listenbrainz.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={})

    mock_requests.add(
        "GET",
        f"{API_URL}/user/unknown/playing-now",
        json={"code": 404, "error": "Cannot find user: unknown"},
        status=404,
    )

    event = _make_event(mock_bot, "unknown")
    event.db = mock_db.session()

    results = wrap_hook_response(listenbrainz.listenbrainz, event)
    assert results == [
        ("return", "ListenBrainz error: Cannot find user: unknown."),
    ]


@pytest.mark.asyncio
async def test_listenbrainz_no_account(
    mock_db: MockDB,
    mock_bot_factory,
    freeze_time,
) -> None:
    listenbrainz.table.create(mock_db.engine)
    listenbrainz.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={})

    event = _make_event(mock_bot, "")
    event.db = mock_db.session()

    results = wrap_hook_response(listenbrainz.listenbrainz, event)
    assert results == [
        ("message", ("foo", f".listenbrainz {event.hook.doc}"), {}),
    ]
    assert mock_db.get_data(listenbrainz.table) == []


@pytest.mark.asyncio
async def test_listenbrainz_dontsave(
    mock_db: MockDB,
    mock_bot_factory,
    mock_requests: RequestsMock,
    freeze_time,
) -> None:
    listenbrainz.table.create(mock_db.engine)
    listenbrainz.load_cache(mock_db.session())
    mock_bot = mock_bot_factory(config={})
    _add_now_playing_playback(mock_requests, "mockuser", True, 156432453)

    event = _make_event(mock_bot, "mockuser dontsave")
    event.db = mock_db.session()

    results = wrap_hook_response(listenbrainz.listenbrainz, event)
    assert results == [
        (
            "return",
            (
                "m\u200bockuser is listening to "
                "\"some track\" by \x02some artist\x0f "
                "from the album \x02some album\x0f."
            ),
        )
    ]
    assert mock_db.get_data(listenbrainz.table) == []
