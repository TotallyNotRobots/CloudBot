import re
from copy import deepcopy
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from googlemaps.exceptions import ApiError

from cloudbot.event import CommandEvent
from cloudbot.util.func_utils import call_with_args
from plugins import weather
from tests.util import HookResult, wrap_hook_response


@pytest.mark.parametrize(
    "bearing,direction",
    [
        (360, "N"),
        (0, "N"),
        (1, "N"),
        (15, "NNE"),
        (30, "NNE"),
        (45, "NE"),
        (60, "ENE"),
        (75, "ENE"),
        (90, "E"),
        (105, "ESE"),
        (120, "ESE"),
        (135, "SE"),
        (150, "SSE"),
        (165, "SSE"),
        (180, "S"),
        (348.75, "N"),
        (348.74, "NNW"),
    ],
)
def test_wind_direction(bearing, direction):
    assert weather.bearing_to_card(bearing) == direction


def test_wind_dir_error():
    with pytest.raises(ValueError):
        weather.bearing_to_card(400)


@pytest.mark.parametrize(
    "temp_f,temp_c",
    [
        (32, 0),
        (212, 100),
        (-40, -40),
    ],
)
def test_temp_convert(temp_f, temp_c):
    assert weather.convert_f2c(temp_f) == temp_c


@pytest.mark.parametrize(
    "mph,kph",
    [
        (0, 0),
        (20, 32.18688),
        (43, 69.201792),
    ],
)
def test_mph_to_kph(mph, kph):
    assert weather.mph_to_kph(mph) == kph


FIO_DATA: Dict[str, Any] = {
    "json": {
        "currently": {
            "summary": "foobar",
            "windSpeed": 12.2,
            "windBearing": 128,
            "temperature": 68,
            "humidity": 0.45,
        },
        "daily": {
            "data": [
                {
                    "summary": "foobar",
                    "temperatureHigh": 64,
                    "temperatureLow": 57,
                    "windSpeed": 15,
                    "windBearing": 140,
                    "humidity": 0.45,
                },
                {
                    "summary": "foobar",
                    "temperatureHigh": 64,
                    "temperatureLow": 57,
                    "windSpeed": 15,
                    "windBearing": 140,
                    "humidity": 0.45,
                },
                {
                    "summary": "foobar",
                    "temperatureHigh": 64,
                    "temperatureLow": 57,
                    "windSpeed": 15,
                    "windBearing": 140,
                    "humidity": 0.45,
                },
                {
                    "summary": "foobar",
                    "temperatureHigh": 64,
                    "temperatureLow": 57,
                    "windSpeed": 15,
                    "windBearing": 140,
                    "humidity": 0.45,
                },
                {
                    "summary": "some summary",
                    "temperatureHigh": 64,
                    "temperatureLow": 57,
                    "windSpeed": 15,
                    "windBearing": 140,
                    "humidity": 0.45,
                },
            ]
        },
    },
    "headers": {
        "Cache-Control": "",
        "Expires": "",
        "X-Forecast-API-Calls": "",
        "X-Response-Time": "",
    },
}


def setup_api(
    mock_requests,
    mock_db,
    event_loop,
    mock_bot_factory,
):
    bot = mock_bot_factory(
        loop=event_loop,
        config={
            "api_keys": {
                "google_dev_key": "AIzatestapikey",
                "darksky": "abc12345" * 4,
            }
        },
        db=mock_db,
    )

    return_value = {
        "status": "OK",
        "results": [
            {
                "geometry": {
                    "location": {
                        "lat": 30.123,
                        "lng": 123.456,
                    }
                },
                "formatted_address": "123 Test St, Example City, CA",
            }
        ],
    }
    mock_requests.add(
        "GET",
        "https://maps.googleapis.com/maps/api/geocode/json",
        json=return_value,
    )
    weather.create_maps_api(bot)
    weather.location_cache.clear()

    return bot


def test_rounding(
    mock_bot_factory, mock_requests, patch_try_shorten, mock_db, event_loop
):
    bot = setup_api(mock_requests, mock_db, event_loop, mock_bot_factory)

    conn = MagicMock()
    conn.config = {}

    conn.bot = bot

    cmd_event = CommandEvent(
        text="",
        cmd_prefix=".",
        triggered_command="we",
        hook=MagicMock(),
        bot=bot,
        conn=conn,
        channel="#foo",
        nick="foobar",
    )

    weather.location_cache.append(("foobar", "test location"))

    new_data = deepcopy(FIO_DATA)

    new_data["json"]["currently"]["temperature"] = 31.9

    mock_requests.add(
        "GET",
        re.compile(r"^https://api\.darksky\.net/forecast/.*"),
        **new_data,
    )

    out_text = (
        "(foobar) \x02Current\x02: foobar, 32F/0C\x0f; \x02High\x02: 64F/18C\x0f; "
        "\x02Low\x02: 57F/14C\x0f; \x02Humidity\x02: 45%\x0f; "
        "\x02Wind\x02: 12MPH/20KPH SE\x0f "
        "-- 123 Test St, Example City, CA - "
        "\x1fhttps://darksky.net/forecast/30.123,123.456\x0f "
        "(\x1dTo get a forecast, use .fc\x1d)"
    )

    calls: List[HookResult] = [
        HookResult(
            "message",
            (
                "#foo",
                out_text,
            ),
        )
    ]

    assert wrap_hook_response(weather.weather, cmd_event) == calls


def test_find_location(
    mock_bot_factory, mock_requests, patch_try_shorten, mock_db, event_loop
):
    bot = mock_bot_factory(config={}, db=mock_db, loop=event_loop)
    weather.create_maps_api(bot)
    weather.location_cache.clear()
    assert weather.data.maps_api is None

    bot = setup_api(
        mock_requests,
        mock_db,
        event_loop,
        mock_bot_factory,
    )

    assert weather.find_location("Foo Bar") == {
        "lat": 30.123,
        "lng": 123.456,
        "address": "123 Test St, Example City, CA",
    }

    conn = MagicMock()
    conn.config = {}

    conn.bot = bot

    cmd_event = CommandEvent(
        text="",
        cmd_prefix=".",
        triggered_command="we",
        hook=MagicMock(),
        bot=bot,
        conn=conn,
        channel="#foo",
        nick="foobar",
    )

    cmd_event.hook.required_args = ["db"]
    cmd_event.hook.doc = "- foobar"

    cmd_event.prepare_threaded()

    assert wrap_hook_response(weather.weather, cmd_event) == [
        ("notice", ("foobar", ".we - foobar"), {})
    ]
    weather.location_cache.append(("foobar", "test location"))

    mock_requests.add(
        "GET",
        re.compile(r"^https://api\.darksky\.net/forecast/.*"),
        **FIO_DATA,
    )
    assert wrap_hook_response(weather.weather, cmd_event) == [
        (
            "message",
            (
                "#foo",
                "(foobar) \x02Current\x02: foobar, 68F/20C\x0f; \x02High\x02: 64F/18C\x0f; "
                "\x02Low\x02: 57F/14C\x0f; \x02Humidity\x02: 45%\x0f; "
                "\x02Wind\x02: 12MPH/20KPH SE\x0f "
                "-- 123 Test St, Example City, CA - "
                "\x1fhttps://darksky.net/forecast/30.123,123.456\x0f "
                "(\x1dTo get a forecast, use .fc\x1d)",
            ),
            {},
        )
    ]
    assert wrap_hook_response(weather.forecast, cmd_event) == [
        (
            "message",
            (
                "#foo",
                "(foobar) \x02Today\x02: foobar; High: 64F/18C; Low: 57F/14C; "
                "Humidity: 45%; Wind: 15MPH/24KPH SE | "
                "\x02Tomorrow\x02: foobar; High: 64F/18C; "
                "Low: 57F/14C; Humidity: 45%; Wind: 15MPH/24KPH SE "
                "-- 123 Test St, Example City, CA - "
                "\x1fhttps://darksky.net/forecast/30.123,123.456\x0f",
            ),
            {},
        )
    ]

    mock_requests.reset()
    mock_requests.add(
        "GET",
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={"status": "foobar"},
    )

    response: List[HookResult] = []
    with pytest.raises(ApiError):
        wrap_hook_response(weather.weather, cmd_event, response)

    assert response == [
        ("message", ("#foo", "(foobar) API Error occurred."), {})
    ]

    bot.config["api_keys"]["google_dev_key"] = None
    bot.config.load_config()
    weather.create_maps_api(bot)
    assert wrap_hook_response(weather.weather, cmd_event) == [
        ("return", "This command requires a Google Developers Console API key.")
    ]
    assert wrap_hook_response(weather.forecast, cmd_event) == [
        ("return", "This command requires a Google Developers Console API key.")
    ]

    bot.config["api_keys"]["darksky"] = None
    bot.config.load_config()
    weather.create_maps_api(bot)
    assert wrap_hook_response(weather.weather, cmd_event) == [
        ("return", "This command requires a DarkSky API key.")
    ]
    assert wrap_hook_response(weather.forecast, cmd_event) == [
        ("return", "This command requires a DarkSky API key.")
    ]

    # Test DB storage
    bot.config.update(
        {
            "api_keys": {
                "google_dev_key": "AIzatestapikey",
                "darksky": "abc12345" * 4,
            }
        }
    )
    bot.config.load_config()
    weather.create_maps_api(bot)
    weather.table.create(mock_db.engine, checkfirst=True)
    cmd_event.db = mock_db.session()
    cmd_event.text = "my location"

    weather.load_cache(mock_db.session())
    mock_requests.reset()
    setup_api(
        mock_requests,
        mock_db,
        event_loop,
        mock_bot_factory,
    )
    mock_requests.add(
        "GET",
        re.compile(r"^https://api\.darksky\.net/forecast/.*"),
        **FIO_DATA,
    )

    (loc, data), err = call_with_args(weather.check_and_parse, cmd_event)
    assert loc == {
        "address": "123 Test St, Example City, CA",
        "lat": 30.123,
        "lng": 123.456,
    }
    assert data is not None
    assert err is None

    assert weather.location_cache == [(cmd_event.nick, cmd_event.text)]

    db_data = mock_db.session().execute(weather.table.select()).fetchall()
    assert len(db_data) == 1
    assert list(db_data[0]) == [cmd_event.nick, cmd_event.text]


def test_update_location(mock_db):
    weather.table.create(mock_db.engine, checkfirst=True)

    db = mock_db.session()

    nick = "testuser"
    loc = "testloc"

    db.execute(weather.table.insert().values(nick=nick, loc=loc))
    db.commit()

    weather.load_cache(db)

    weather.add_location(nick, "newloc", db)

    db_data = mock_db.session().execute(weather.table.select()).fetchall()

    table_data = [list(row) for row in db_data]

    assert table_data == [[nick, "newloc"]]


def test_parse_no_results(
    mock_bot_factory, mock_requests, patch_try_shorten, mock_db, event_loop
):
    mock_requests.add(
        "GET",
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={
            "status": "OK",
            "results": [],
        },
    )

    weather.table.create(mock_db.engine, True)

    bot = mock_bot_factory(
        loop=event_loop,
        config={
            "api_keys": {
                "google_dev_key": "AIzatestapikey",
                "darksky": "abc12345" * 4,
            }
        },
        db=mock_db,
    )

    weather.create_maps_api(bot)

    conn = MagicMock()
    conn.config = {}

    conn.bot = bot

    cmd_event = CommandEvent(
        text="myloc",
        cmd_prefix=".",
        triggered_command="we",
        hook=MagicMock(),
        bot=bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )

    cmd_event.hook.required_args = ["event", "db"]
    cmd_event.hook.doc = "- foobar"

    cmd_event.prepare_threaded()

    res = wrap_hook_response(weather.check_and_parse, cmd_event)
    assert res == [("return", (None, "Unable to find location 'myloc'"))]
