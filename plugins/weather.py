from fractions import Fraction
from typing import Optional

import googlemaps
from forecastiopy.ForecastIO import ForecastIO
from googlemaps.exceptions import ApiError
from sqlalchemy import Table, Column, PrimaryKeyConstraint, String

from cloudbot import hook
from cloudbot.util import web, database


class PluginData:
    maps_api = None  # type: Optional[googlemaps.Client]


data = PluginData()

# Define database table

table = Table(
    "weather",
    database.metadata,
    Column('nick', String),
    Column('loc', String),
    PrimaryKeyConstraint('nick')
)

location_cache = []

BEARINGS = (
    'N', 'NNE',
    'NE', 'ENE',
    'E', 'ESE',
    'SE', 'SSE',
    'S', 'SSW',
    'SW', 'WSW',
    'W', 'WNW',
    'NW', 'NNW',
)

# math constants
NUM_BEARINGS = len(BEARINGS)
BEARING_SECTION = 360 / NUM_BEARINGS
BEARING_RANGE = BEARING_SECTION / 2


def bearing_to_card(bearing):
    if bearing > 360 or bearing < 0:
        raise ValueError("Invalid wind bearing: {}".format(bearing))

    # Derived from values from http://snowfence.umn.edu/Components/winddirectionanddegreeswithouttable3.htm
    index = int(NUM_BEARINGS * (((bearing + BEARING_RANGE) % 360) / 360))
    return BEARINGS[index]


def convert_f2c(temp):
    """
    Convert temperature in Fahrenheit to Celsios
    """
    return (temp - 32) * Fraction(5, 9)


def mph_to_kph(mph):
    return mph * 1.609344


def find_location(location, bias=None):
    """
    Takes a location as a string, and returns a dict of data
    :param location: string
    :param bias: The region to bias answers towards
    :return: dict
    """
    json = data.maps_api.geocode(location, region=bias)[0]
    out = json['geometry']['location']
    out['address'] = json['formatted_address']
    return out


def add_location(nick, location, db):
    test = dict(location_cache)
    location = str(location)
    if nick.lower() in test:
        db.execute(table.update().values(loc=location.lower()).where(table.c.nick == nick.lower()))
        db.commit()
        load_cache(db)
    else:
        db.execute(table.insert().values(nick=nick.lower(), loc=location.lower()))
        db.commit()
        load_cache(db)


@hook.on_start
def load_cache(db):
    new_cache = []
    for row in db.execute(table.select()):
        nick = row["nick"]
        location = row["loc"]
        new_cache.append((nick, location))

    location_cache.clear()
    location_cache.extend(new_cache)


@hook.on_start()
def create_maps_api(bot):
    google_key = bot.config.get_api_key("google_dev_key")
    if google_key:
        data.maps_api = googlemaps.Client(google_key)
    else:
        data.maps_api = None


def get_location(nick):
    """looks in location_cache for a saved location"""
    location = [row[1] for row in location_cache if nick.lower() == row[0]]
    if not location:
        return

    location = location[0]
    return location


@hook.command("weather", "we", autohelp=False)
def weather(text, reply, db, nick, notice_doc, bot):
    """<location> - Gets weather data for <location>."""
    ds_key = bot.config.get_api_key("darksky")
    if not ds_key:
        return "This command requires a DarkSky API key."

    if not data.maps_api:
        return "This command requires a Google Developers Console API key."

    # If no input try the db
    if not text:
        location = get_location(nick)
        if not location:
            notice_doc()
            return
    else:
        location = text

    # Change this in the config to a ccTLD code (eg. uk, nz)
    # to make results more targeted towards that specific country.
    # <https://developers.google.com/maps/documentation/geocoding/#RegionCodes>
    bias = bot.config.get('location_bias_cc')
    # use find_location to get location data from the user input
    try:
        location_data = find_location(location, bias=bias)
    except ApiError:
        reply("API Error occurred.")
        raise

    fio = ForecastIO(
        ds_key, units=ForecastIO.UNITS_US,
        latitude=location_data['lat'], longitude=location_data['lng']
    )

    daily_conditions = fio.get_daily()['data']
    current = fio.get_currently()
    today, tomorrow = daily_conditions[:2]
    current['name'] = 'Current'
    today['name'] = 'Today'
    tomorrow['name'] = 'Tomorrow'

    for forecast in (current, today, tomorrow):
        wind_speed = forecast['windSpeed']
        forecast.update(
            wind_direction=bearing_to_card(forecast['windBearing']),
            wind_speed_mph=wind_speed,
            wind_speed_kph=mph_to_kph(wind_speed),
            summary=forecast['summary'].rstrip('.'),
        )

    current.update(
        temp_f=current['temperature'],
        temp_c=convert_f2c(current['temperature'])
    )

    for day_forecast in (today, tomorrow):
        high = day_forecast['temperatureHigh']
        low = day_forecast['temperatureLow']
        day_forecast.update(
            temp_high_f=high,
            temp_high_c=convert_f2c(high),
            temp_low_f=low,
            temp_low_c=convert_f2c(low),
        )

    current_str = "\x02{name}\x02: {summary}, {temp_f:.3g}F/{temp_c:.3g}C " \
                  "{humidity:.0%}, " \
                  "Wind: {wind_speed_mph:.3g}MPH/{wind_speed_kph:.3g}KPH " \
                  "{wind_direction}"
    day_str = "\x02{name}\x02: {summary}, " \
              "High: {temp_high_f:.3g}F/{temp_high_c:.3g}C, " \
              "Low: {temp_low_f:.3g}F/{temp_low_c:.3g}C"

    url = web.try_shorten(
        'https://darksky.net/forecast/{lat:.3f},{lng:.3f}'.format_map(
            location_data
        )
    )

    reply(
        "{place} - {current_str}, "
        "{today_str}, {tomorrow_str} "
        "- {url}".format(
            place=location_data['address'],
            current_str=current_str.format_map(current),
            today_str=day_str.format_map(today),
            tomorrow_str=day_str.format_map(tomorrow),
            url=url
        )
    )

    if text:
        add_location(nick, location, db)
