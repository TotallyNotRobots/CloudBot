import math
import re

import pytest
from googlemaps.exceptions import ApiError
from mock import MagicMock

from cloudbot.config import Config
from cloudbot.event import CommandEvent
from cloudbot.util.func_utils import call_with_args


class MockConfig(Config):
    def load_config(self):
        self._api_keys.clear()


class MockBot:
    def __init__(self, config):
        self.config = MockConfig(self, config)


@pytest.mark.parametrize('bearing,direction', [
    (360, 'N'),
    (0, 'N'),
    (1, 'N'),
    (15, 'NNE'),
    (30, 'NNE'),
    (45, 'NE'),
    (60, 'ENE'),
    (75, 'ENE'),
    (90, 'E'),
    (105, 'ESE'),
    (120, 'ESE'),
    (135, 'SE'),
    (150, 'SSE'),
    (165, 'SSE'),
    (180, 'S'),
    (348.75, 'N'),
    (348.74, 'NNW'),
])
def test_wind_direction(bearing, direction):
    from plugins.weather import bearing_to_card
    assert bearing_to_card(bearing) == direction


def test_wind_dir_error():
    with pytest.raises(ValueError):
        from plugins.weather import bearing_to_card
        bearing_to_card(400)


@pytest.mark.parametrize('temp_f,temp_c', [
    (32, 0),
    (212, 100),
    (-40, -40),
])
def test_temp_convert(temp_f, temp_c):
    from plugins.weather import convert_f2c
    assert convert_f2c(temp_f) == temp_c


@pytest.mark.parametrize('mph,kph', [
    (0, 0),
    (43, 69.2),
])
def test_mph_to_kph(mph, kph):
    from plugins.weather import mph_to_kph
    assert math.isclose(mph_to_kph(mph), kph, rel_tol=1e-3)


FIO_DATA = {
    'json': {
        'currently': {
            'summary': 'foobar',
            'windSpeed': 12.2,
            'windBearing': 128,
            'temperature': 68,
            'humidity': .45,
        },
        'daily': {
            'data': [
                {
                    'summary': 'foobar',
                    'temperatureHigh': 64,
                    'temperatureLow': 57,
                    'windSpeed': 15,
                    'windBearing': 140,
                    'humidity': .45,
                },
                {
                    'summary': 'foobar',
                    'temperatureHigh': 64,
                    'temperatureLow': 57,
                    'windSpeed': 15,
                    'windBearing': 140,
                    'humidity': .45,
                },
                {
                    'summary': 'foobar',
                    'temperatureHigh': 64,
                    'temperatureLow': 57,
                    'windSpeed': 15,
                    'windBearing': 140,
                    'humidity': .45,
                },
                {
                    'summary': 'foobar',
                    'temperatureHigh': 64,
                    'temperatureLow': 57,
                    'windSpeed': 15,
                    'windBearing': 140,
                    'humidity': .45,
                },
                {
                    'summary': 'foobar',
                    'temperatureHigh': 64,
                    'temperatureLow': 57,
                    'windSpeed': 15,
                    'windBearing': 140,
                    'humidity': .45,
                },
            ]
        },
    },
    'headers': {
        'Cache-Control': '',
        'Expires': '',
        'X-Forecast-API-Calls': '',
        'X-Response-Time': '',
    }
}


def test_find_location(mock_requests, patch_try_shorten, mock_db):
    from plugins import weather
    bot = MockBot({})
    weather.create_maps_api(bot)
    assert weather.data.maps_api is None
    bot = MockBot({
        'api_keys': {
            'google_dev_key': 'AIzatestapikey',
            'darksky': 'abc12345' * 4,
        }
    })

    return_value = {
        'status': 'OK',
        'results': [
            {
                'geometry': {
                    'location': {
                        'lat': 30.123,
                        'lng': 123.456,
                    }
                },
                'formatted_address': '123 Test St, Example City, CA'
            }
        ]
    }
    mock_requests.add(
        mock_requests.GET, 'https://maps.googleapis.com/maps/api/geocode/json',
        json=return_value
    )
    weather.create_maps_api(bot)

    assert weather.find_location('Foo Bar') == {
        'lat': 30.123,
        'lng': 123.456,
        'address': '123 Test St, Example City, CA',
    }

    cmd_event = CommandEvent(
        text='', cmd_prefix='.',
        triggered_command='we',
        hook=MagicMock(), bot=bot,
        conn=MagicMock(), channel='#foo',
        nick='foobar'
    )

    call_with_args(weather.weather, cmd_event)
    weather.location_cache.append(('foobar', 'test location'))

    mock_requests.add(
        mock_requests.GET, re.compile(r'^https://api\.darksky\.net/forecast/.*'),
        **FIO_DATA
    )
    call_with_args(weather.weather, cmd_event)
    call_with_args(weather.forecast, cmd_event)

    mock_requests.reset()
    mock_requests.add(
        mock_requests.GET, 'https://maps.googleapis.com/maps/api/geocode/json',
        json={'status': 'foobar'}
    )

    with pytest.raises(ApiError):
        call_with_args(weather.weather, cmd_event)

    bot.config['api_keys']['google_dev_key'] = None
    bot.config.load_config()
    weather.create_maps_api(bot)
    call_with_args(weather.weather, cmd_event)
    call_with_args(weather.forecast, cmd_event)

    bot.config['api_keys']['darksky'] = None
    bot.config.load_config()
    weather.create_maps_api(bot)
    call_with_args(weather.weather, cmd_event)
    call_with_args(weather.forecast, cmd_event)

    # Test DB storage
    bot.config.update({'api_keys': {
        'google_dev_key': 'AIzatestapikey',
        'darksky': 'abc12345' * 4,
    }})
    bot.config.load_config()
    weather.create_maps_api(bot)
    weather.table.create(mock_db.engine, checkfirst=True)
    cmd_event.db = mock_db.session()
    cmd_event.text = 'my location'

    weather.load_cache(mock_db.session())
    mock_requests.reset()
    mock_requests.add(
        mock_requests.GET, 'https://maps.googleapis.com/maps/api/geocode/json',
        json=return_value
    )
    mock_requests.add(
        mock_requests.GET, re.compile(r'^https://api\.darksky\.net/forecast/.*'),
        **FIO_DATA
    )

    _, err = call_with_args(weather.check_and_parse, cmd_event)
    assert not err

    assert weather.location_cache == [(cmd_event.nick, cmd_event.text)]

    db_data = mock_db.session().execute(weather.table.select()).fetchall()
    assert len(db_data) == 1
    assert list(db_data[0]) == [cmd_event.nick, cmd_event.text]
