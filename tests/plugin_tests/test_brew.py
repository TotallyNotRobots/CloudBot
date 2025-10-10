from typing import Any
from unittest.mock import MagicMock

import pytest
from responses.matchers import query_param_matcher

from cloudbot.bot import bot
from plugins import brew


@pytest.mark.asyncio
async def test_no_key(mock_bot_factory, mock_requests, unset_bot):
    bot.set(mock_bot_factory(config={"api_keys": {}}))
    reply = MagicMock()
    result = brew.brew("some text", reply)

    reply.assert_not_called()

    assert result == "No brewerydb API key set."


@pytest.mark.asyncio
async def test_empty_body(mock_bot_factory, mock_requests, unset_bot):
    bot.set(mock_bot_factory(config={"api_keys": {"brewerydb": "APIKEY"}}))
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
    result = brew.brew("some text", reply)

    reply.assert_not_called()

    assert result == "No results found."


@pytest.mark.asyncio
async def test_no_results(mock_bot_factory, mock_requests, unset_bot):
    bot.set(mock_bot_factory(config={"api_keys": {"brewerydb": "APIKEY"}}))
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
    result = brew.brew("some text", reply)

    reply.assert_not_called()

    assert result == "No results found."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "style,abv,website,out",
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
    mock_bot_factory,
    mock_requests,
    unset_bot,
    style,
    abv,
    website,
    out,
):
    bot.set(mock_bot_factory(config={"api_keys": {"brewerydb": "APIKEY"}}))
    brewery = {"name": "foo"}
    if website:
        brewery["website"] = website

    beer: dict[str, Any] = {
        "breweries": [
            brewery,
        ],
        "nameDisplay": "fooBar",
    }
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
        json={
            "totalResults": 1,
            "data": [beer],
        },
    )

    reply = MagicMock()
    result = brew.brew("some text", reply)

    reply.assert_not_called()

    assert result == out
