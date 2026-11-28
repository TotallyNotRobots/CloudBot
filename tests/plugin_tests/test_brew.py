from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from responses.matchers import query_param_matcher

from plugins import brew

if TYPE_CHECKING:
    from responses import RequestsMock

    from tests.util.mock_bot import MockBotFactory


@pytest.mark.asyncio
async def test_no_key(mock_bot_factory: MockBotFactory) -> None:
    bot = mock_bot_factory(config={"api_keys": {}})
    reply = MagicMock()
    result = brew.brew("some text", reply, bot)

    reply.assert_not_called()

    assert result == "No brewerydb API key set."


@pytest.mark.asyncio
async def test_empty_body(
    mock_bot_factory: MockBotFactory, mock_requests: RequestsMock
) -> None:
    bot = mock_bot_factory(config={"api_keys": {"brewerydb": "APIKEY"}})
    mock_requests.add(
        "GET",
        "http://api.brewerydb.com/v2/search",
        json={},
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "key": "APIKEY",
                    "type": "beer",
                    "withBreweries": "Y",
                    "q": "some text",
                }
            )
        ],
    )

    reply = MagicMock()
    result = brew.brew("some text", reply, bot)

    reply.assert_not_called()

    assert result == "No results found."


@pytest.mark.asyncio
async def test_no_results(
    mock_bot_factory: MockBotFactory, mock_requests: RequestsMock
) -> None:
    bot = mock_bot_factory(config={"api_keys": {"brewerydb": "APIKEY"}})
    mock_requests.add(
        "GET",
        "http://api.brewerydb.com/v2/search",
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "key": "APIKEY",
                    "type": "beer",
                    "withBreweries": "Y",
                    "q": "some text",
                }
            )
        ],
        json={"totalResults": 0},
    )

    reply = MagicMock()
    result = brew.brew("some text", reply, bot)

    reply.assert_not_called()

    assert result == "No results found."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("style", "abv", "website", "out"),
    [
        (
            None,
            None,
            None,
            "fooBar by foo (unknown style, ?.?% ABV) - [no website found]",
        ),
        (
            "ipa",
            None,
            None,
            "fooBar by foo (ipa, ?.?% ABV) - [no website found]",
        ),
        (
            None,
            "1.5",
            None,
            "fooBar by foo (unknown style, 1.5% ABV) - [no website found]",
        ),
        (
            None,
            None,
            "https://example.com",
            "fooBar by foo (unknown style, ?.?% ABV) - https://example.com",
        ),
    ],
)
async def test_results(
    mock_bot_factory: MockBotFactory,
    mock_requests: RequestsMock,
    style: str | None,
    abv: str | None,
    website: str | None,
    out: str,
) -> None:
    bot = mock_bot_factory(config={"api_keys": {"brewerydb": "APIKEY"}})
    brewery = {"name": "foo"}
    if website:
        brewery["website"] = website

    beer: dict[str, Any] = {"breweries": [brewery], "nameDisplay": "fooBar"}
    if abv:
        beer["abv"] = abv

    if style:
        beer["style"] = {"shortName": style}

    mock_requests.add(
        "GET",
        "http://api.brewerydb.com/v2/search",
        match=[
            query_param_matcher(
                {
                    "format": "json",
                    "key": "APIKEY",
                    "type": "beer",
                    "withBreweries": "Y",
                    "q": "some text",
                }
            )
        ],
        json={"totalResults": 1, "data": [beer]},
    )

    reply = MagicMock()
    result = brew.brew("some text", reply, bot)

    reply.assert_not_called()

    assert result == out
