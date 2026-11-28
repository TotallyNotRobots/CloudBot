from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from plugins import steam_store

if TYPE_CHECKING:
    from pydantic import JsonValue
    from responses import RequestsMock


@pytest.mark.parametrize(
    ("is_free", "price_now", "price_original", "price_str"),
    [
        (True, None, None, "\2free\2"),
        (False, 500, 500, "\x02$5.00\x02"),
        (False, 100, 500, "\x02$1.00\x02 (was \x02$5.00\x02)"),
    ],
)
def test_format_game(
    mock_requests: RequestsMock,
    is_free: bool,
    price_now: int | None,
    price_original: int | None,
    price_str: str,
) -> None:
    appid = "appid"
    data: dict[str, JsonValue] = {
        "name": "foo",
        "about_the_game": "<h1>foo</h1>bar",
        "genres": [{"description": "foobar"}, {"description": "foobar1"}],
        "release_date": {"coming_soon": False, "date": "10/24/16"},
        "is_free": is_free,
        "steam_appid": "foobar",
    }
    if price_now:
        data["price_overview"] = {"final": price_now, "initial": price_original}

    mock_requests.add(
        "GET",
        "http://store.steampowered.com/api/appdetails/?appids=appid",
        json={appid: {"data": data}},
    )
    res = steam_store.format_game(appid)

    parts = [
        "\x02foo\x02",
        "foobar",
        "\x02foobar, foobar1\x02",
        "released \x0210/24/16\x02",
        price_str,
        "http://store.steampowered.com/app/foobar/",
    ]
    assert res == " - ".join(filter(None, parts))
