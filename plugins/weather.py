import math
from fractions import Fraction
from typing import List, Optional, Tuple

import googlemaps
from forecastiopy.ForecastIO import ForecastIO
from googlemaps.exceptions import ApiError
from sqlalchemy import Column, PrimaryKeyConstraint, String, Table

from cloudbot import hook
from cloudbot.util import colors, database, web

Api = Optional[googlemaps.Client]


class PluginData:
    maps_api = None  # type: Api


data = PluginData()

# Define database table

table = Table(
    "weather",
    database.metadata,
    Column("nick", String),
    Column("loc", String),
    PrimaryKeyConstraint("nick"),
)

location_cache: List[Tuple[str, str]] = []

BEARINGS = (
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
)

# math constants
NUM_BEARINGS = len(BEARINGS)
MAX_DEGREES = 360
BEARING_SECTION = MAX_DEGREES / NUM_BEARINGS
BEARING_RANGE = BEARING_SECTION / 2

# miles to kilometres (1 mile = 63360 in = 160934.4 cm = 1.609344 km)
MI_TO_KM = Fraction(1609344, 1000000)


def bearing_to_card(bearing):
    if bearing > MAX_DEGREES or bearing < 0:
        raise ValueError("Invalid wind bearing: {}".format(bearing))

    # Derived from values from http://snowfence.umn.edu/Components/winddirectionanddegreeswithouttable3.htm
    adj_bearing = bearing + BEARING_RANGE
    mod_bearing = adj_bearing % MAX_DEGREES
    percent = mod_bearing / MAX_DEGREES
    adj_position = NUM_BEARINGS * percent
    index = math.floor(adj_position)
    return BEARINGS[index]


def convert_f2c(temp):
    """
    Convert temperature in Fahrenheit to Celsius
    """
    return float((temp - 32) * Fraction(5, 9))


def round_temp(temp):
    return round(temp)


def mph_to_kph(mph):
    return float(mph * MI_TO_KM)


class LocationNotFound(Exception):
    def __init__(self, location):
        super().__init__("Unable to find location {!r}".format(location))
        self.location = location


def find_location(location, bias=None):
    """
    Takes a location as a string, and returns a dict of data
    """
    results = data.maps_api.geocode(location, region=bias)
    if not results:
        raise LocationNotFound(location)

    json = results[0]
    out = json["geometry"]["location"]
    out["address"] = json["formatted_address"]
    return out


def add_location(nick, location, db):
    test = dict(location_cache)
    location = str(location)
    if nick.lower() in test:
        db.execute(
            table.update()
            .values(loc=location.lower())
            .where(table.c.nick == nick.lower())
        )
    else:
        db.execute(
            table.insert().values(nick=nick.lower(), loc=location.lower())
        )

    db.commit()
    load_cache(db)


@hook.on_start()
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
        return None

    return location[0]


def check_and_parse(event, db):
    """
    Check for the API keys and parse the location from user input
    """
    ds_key = event.bot.config.get_api_key("darksky")
    if not ds_key:
        return None, "This command requires a DarkSky API key."

    if not data.maps_api:
        return (
            None,
            "This command requires a Google Developers Console API key.",
        )

    # If no input try the db
    if not event.text:
        location = get_location(event.nick)
        if not location:
            event.notice_doc()
            return None, None
    else:
        location = event.text
        add_location(event.nick, location, db)

    # Change this in the config to a ccTLD code (eg. uk, nz)
    # to make results more targeted towards that specific country.
    # <https://developers.google.com/maps/documentation/geocoding/#RegionCodes>
    bias = event.bot.config.get("location_bias_cc")
    # use find_location to get location data from the user input
    try:
        location_data = find_location(location, bias=bias)
    except ApiError:
        event.reply("API Error occurred.")
        raise
    except LocationNotFound as e:
        return None, str(e)

    fio = ForecastIO(
        ds_key,
        units=ForecastIO.UNITS_US,
        latitude=location_data["lat"],
        longitude=location_data["lng"],
    )

    return (location_data, fio), None


@hook.command("weather", "we", autohelp=False)
def weather(reply, db, triggered_prefix, event):
    """<location> - Gets weather data for <location>."""
    res, err = check_and_parse(event, db)
    if not res:
        return err

    location_data, fio = res

    daily_conditions = fio.get_daily()["data"]
    current = fio.get_currently()
    today = daily_conditions[0]
    wind_speed = current["windSpeed"]
    today_high = today["temperatureHigh"]
    today_low = today["temperatureLow"]
    current.update(
        name="Current",
        wind_direction=bearing_to_card(current["windBearing"]),
        wind_speed_mph=wind_speed,
        wind_speed_kph=mph_to_kph(wind_speed),
        summary=current["summary"].rstrip("."),
        temp_f=round_temp(current["temperature"]),
        temp_c=round_temp(convert_f2c(current["temperature"])),
        temp_high_f=round_temp(today_high),
        temp_high_c=round_temp(convert_f2c(today_high)),
        temp_low_f=round_temp(today_low),
        temp_low_c=round_temp(convert_f2c(today_low)),
    )

    parts = [
        ("Current", "{summary}, {temp_f}F/{temp_c}C"),
        ("High", "{temp_high_f}F/{temp_high_c}C"),
        ("Low", "{temp_low_f}F/{temp_low_c}C"),
        ("Humidity", "{humidity:.0%}"),
        (
            "Wind",
            "{wind_speed_mph:.0f}MPH/{wind_speed_kph:.0f}KPH {wind_direction}",
        ),
    ]

    current_str = "; ".join(
        colors.parse("$(b){}$(b): {}$(clear)".format(part[0], part[1]))
        for part in parts
    )

    url = web.try_shorten(
        "https://darksky.net/forecast/{lat:.3f},{lng:.3f}".format_map(
            location_data
        )
    )

    reply(
        colors.parse(
            "{current_str} -- "
            "{place} - "
            "$(ul){url}$(clear) "
            "($(i)To get a forecast, use {cmd_prefix}fc$(i))"
        ).format(
            place=location_data["address"],
            current_str=current_str.format_map(current),
            url=url,
            cmd_prefix=triggered_prefix,
        )
    )

    return None


@hook.command("forecast", "fc", autohelp=False)
def forecast(reply, db, event):
    """<location> - Gets forecast data for <location>."""
    res, err = check_and_parse(event, db)
    if not res:
        return err

    location_data, fio = res

    daily_conditions = fio.get_daily()["data"]
    today, tomorrow, *three_days = daily_conditions[:5]

    today["name"] = "Today"
    tomorrow["name"] = "Tomorrow"

    for day_fc in (today, tomorrow):
        wind_speed = day_fc["windSpeed"]
        day_fc.update(
            wind_direction=bearing_to_card(day_fc["windBearing"]),
            wind_speed_mph=wind_speed,
            wind_speed_kph=mph_to_kph(wind_speed),
            summary=day_fc["summary"].rstrip("."),
        )

    for fc_data in (today, tomorrow, *three_days):
        high = fc_data["temperatureHigh"]
        low = fc_data["temperatureLow"]
        fc_data.update(
            temp_high_f=round_temp(high),
            temp_high_c=round_temp(convert_f2c(high)),
            temp_low_f=round_temp(low),
            temp_low_c=round_temp(convert_f2c(low)),
        )

    parts = [
        ("High", "{temp_high_f:.0f}F/{temp_high_c:.0f}C"),
        ("Low", "{temp_low_f:.0f}F/{temp_low_c:.0f}C"),
        ("Humidity", "{humidity:.0%}"),
        (
            "Wind",
            "{wind_speed_mph:.0f}MPH/{wind_speed_kph:.0f}KPH {wind_direction}",
        ),
    ]

    day_str = colors.parse("$(b){name}$(b): {summary}; ") + "; ".join(
        "{}: {}".format(part[0], part[1]) for part in parts
    )

    url = web.try_shorten(
        "https://darksky.net/forecast/{lat:.3f},{lng:.3f}".format_map(
            location_data
        )
    )

    out_format = "{today_str} | {tomorrow_str} -- {place} - $(ul){url}$(clear)"

    reply(
        colors.parse(out_format).format(
            today_str=day_str.format_map(today),
            tomorrow_str=day_str.format_map(tomorrow),
            place=location_data["address"],
            url=url,
        )
    )
    return None
