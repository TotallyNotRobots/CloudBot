from __future__ import annotations

from typing import TYPE_CHECKING

from plugins import giphy

if TYPE_CHECKING:
    from responses import RequestsMock

    from tests.util.mock_bot import MockBot


def test_giphy(mock_requests: RequestsMock, mock_bot: MockBot) -> None:
    mock_requests.add(
        "GET",
        "http://api.giphy.com/v1/gifs/search?q=foo&limit=10&fmt=json",
        json={"data": [{"rating": None, "embed_url": "foo.bar"}]},
    )
    res = giphy.giphy("foo", mock_bot)
    assert res == "foo.bar - (Powered by GIPHY)"


def test_giphy_rating(mock_requests: RequestsMock, mock_bot: MockBot) -> None:
    mock_requests.add(
        "GET",
        "http://api.giphy.com/v1/gifs/search?q=foo&limit=10&fmt=json",
        json={"data": [{"rating": "PG", "embed_url": "foo.bar"}]},
    )
    res = giphy.giphy("foo", mock_bot)
    assert res == "foo.bar content rating: \x02PG\x02. (Powered by GIPHY)"


def test_giphy_no_results(
    mock_requests: RequestsMock, mock_bot: MockBot
) -> None:
    mock_requests.add(
        "GET",
        "http://api.giphy.com/v1/gifs/search?q=foo&limit=10&fmt=json",
        json={"data": []},
    )
    res = giphy.giphy("foo", mock_bot)
    assert res == "no results found."
