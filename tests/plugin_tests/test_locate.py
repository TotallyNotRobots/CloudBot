from unittest.mock import MagicMock

import pytest
import responses
from responses.matchers import query_param_matcher

from cloudbot.event import CommandEvent
from plugins import locate
from tests.util import wrap_hook_response


@pytest.mark.parametrize(
    "status,out",
    [
        (
            "REQUEST_DENIED",
            "The geocode API is off in the Google Developers Console.",
        ),
        ("ZERO_RESULTS", "No results found."),
        ("OVER_QUERY_LIMIT", "The geocode API quota has run out."),
        ("UNKNOWN_ERROR", "Unknown Error."),
        ("INVALID_REQUEST", "Invalid Request."),
        ("OK", None),
        ("foobar", None),
    ],
)
def test_check_status(status, out) -> None:
    assert locate.check_status(status) == out


def test_locate_no_bias(mock_requests, mock_bot) -> None:
    mock_bot.config.update({"api_keys": {"google_dev_key": "FOOBAR"}})

    conn = MagicMock(bot=mock_bot)
    event = CommandEvent(
        triggered_command="maps",
        cmd_prefix=".",
        hook=MagicMock(),
        text="nyc",
        nick="User",
        user="name",
        host="hostname",
        bot=mock_bot,
        conn=conn,
        channel="#foo",
    )

    mock_requests.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={
            "status": "OK",
            "results": [
                {
                    "address_components": [
                        {
                            "long_name": "New York",
                            "short_name": "New York",
                            "types": ["locality", "political"],
                        },
                        {
                            "long_name": "New York",
                            "short_name": "NY",
                            "types": [
                                "administrative_area_level_1",
                                "political",
                            ],
                        },
                        {
                            "long_name": "United States",
                            "short_name": "US",
                            "types": ["country", "political"],
                        },
                    ],
                    "formatted_address": "New York, NY, USA",
                    "geometry": {
                        "bounds": {
                            "northeast": {"lat": 40.917705, "lng": -73.700169},
                            "southwest": {"lat": 40.476578, "lng": -74.258843},
                        },
                        "location": {"lat": 40.7127753, "lng": -74.0059728},
                        "location_type": "APPROXIMATE",
                        "viewport": {
                            "northeast": {"lat": 40.917705, "lng": -73.700169},
                            "southwest": {"lat": 40.476578, "lng": -74.258843},
                        },
                    },
                    "place_id": "ChIJOwg_06VPwokRYv534QaPC8g",
                    "types": ["locality", "political"],
                }
            ],
        },
        match=[query_param_matcher({"address": "nyc", "key": "FOOBAR"})],
    )

    assert wrap_hook_response(locate.locate, event) == [
        (
            "return",
            "\x02New York, NY, USA\x02 - https://google.com/maps/@40.7127753,-74.0059728,16z/data=!3m1!1e3 (locality)",
        )
    ]


def test_locate_with_bias(mock_requests, mock_bot) -> None:
    mock_bot.config.update(
        {"api_keys": {"google_dev_key": "FOOBAR"}, "location_bias_cc": "us"}
    )

    conn = MagicMock(bot=mock_bot)
    event = CommandEvent(
        triggered_command="maps",
        cmd_prefix=".",
        hook=MagicMock(),
        text="nyc",
        nick="User",
        user="name",
        host="hostname",
        bot=mock_bot,
        conn=conn,
        channel="#foo",
    )

    mock_requests.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={
            "status": "OK",
            "results": [
                {
                    "address_components": [
                        {
                            "long_name": "New York",
                            "short_name": "New York",
                            "types": ["locality", "political"],
                        },
                        {
                            "long_name": "New York",
                            "short_name": "NY",
                            "types": [
                                "administrative_area_level_1",
                                "political",
                            ],
                        },
                        {
                            "long_name": "United States",
                            "short_name": "US",
                            "types": ["country", "political"],
                        },
                    ],
                    "formatted_address": "New York, NY, USA",
                    "geometry": {
                        "bounds": {
                            "northeast": {"lat": 40.917705, "lng": -73.700169},
                            "southwest": {"lat": 40.476578, "lng": -74.258843},
                        },
                        "location": {"lat": 40.7127753, "lng": -74.0059728},
                        "location_type": "APPROXIMATE",
                        "viewport": {
                            "northeast": {"lat": 40.917705, "lng": -73.700169},
                            "southwest": {"lat": 40.476578, "lng": -74.258843},
                        },
                    },
                    "place_id": "ChIJOwg_06VPwokRYv534QaPC8g",
                    "types": ["locality", "political"],
                }
            ],
        },
        match=[
            query_param_matcher(
                {"address": "nyc", "key": "FOOBAR", "region": "us"}
            )
        ],
    )

    assert wrap_hook_response(locate.locate, event) == [
        (
            "return",
            "\x02New York, NY, USA\x02 - https://google.com/maps/@40.7127753,-74.0059728,16z/data=!3m1!1e3 (locality)",
        )
    ]
