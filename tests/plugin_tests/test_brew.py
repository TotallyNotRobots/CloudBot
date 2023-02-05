from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from cloudbot.bot import bot
from plugins import brew


def test_no_key(mock_bot_factory, mock_requests, unset_bot, event_loop):
    bot.set(mock_bot_factory(loop=event_loop, config={"api_keys": {}}))
    reply = MagicMock()
    result = brew.brew("some text", reply)

    reply.assert_not_called()

    assert result == "No brewerydb API key set."


def test_empty_body(mock_bot_factory, mock_requests, unset_bot, event_loop):
    bot.set(
        mock_bot_factory(
            loop=event_loop, config={"api_keys": {"brewerydb": "APIKEY"}}
        )
    )
    mock_requests.add(
        "GET",
        "http://api.brewerydb.com/v2/search"
        "?format=json&key=APIKEY&type=beer&withBreweries=Y&q=some+text",
        match_querystring=True,
        json={},
    )

    reply = MagicMock()
    result = brew.brew("some text", reply)

    reply.assert_not_called()

    assert result == "No results found."


def test_no_results(mock_bot_factory, mock_requests, unset_bot, event_loop):
    bot.set(
        mock_bot_factory(
            loop=event_loop, config={"api_keys": {"brewerydb": "APIKEY"}}
        )
    )
    mock_requests.add(
        "GET",
        "http://api.brewerydb.com/v2/search"
        "?format=json&key=APIKEY&type=beer&withBreweries=Y&q=some+text",
        match_querystring=True,
        json={"totalResults": 0},
    )

    reply = MagicMock()
    result = brew.brew("some text", reply)

    reply.assert_not_called()

    assert result == "No results found."


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
def test_results(
    mock_bot_factory,
    mock_requests,
    unset_bot,
    event_loop,
    style,
    abv,
    website,
    out,
):
    bot.set(
        mock_bot_factory(
            loop=event_loop, config={"api_keys": {"brewerydb": "APIKEY"}}
        )
    )
    brewery = {"name": "foo"}
    if website:
        brewery["website"] = website

    beer: Dict[str, Any] = {
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
        "http://api.brewerydb.com/v2/search"
        "?format=json&key=APIKEY&type=beer&withBreweries=Y&q=some+text",
        match_querystring=True,
        json={
            "totalResults": 1,
            "data": [beer],
        },
    )

    reply = MagicMock()
    result = brew.brew("some text", reply)

    reply.assert_not_called()

    assert result == out
