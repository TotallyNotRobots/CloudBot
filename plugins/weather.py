import math
from fractions import Fraction
from typing import List, Optional, Tuple

import googlemaps
import pyowm
from googlemaps.exceptions import ApiError
from pyowm import OWM
from pyowm.weatherapi25.weather import Weather
from sqlalchemy import Column, PrimaryKeyConstraint, String, Table

from cloudbot import hook
from cloudbot.util import colors, database

Api = Optional[googlemaps.Client]


class PluginData:
    maps_api = None  # type: Api
    owm_api: Optional[OWM] = None


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
        raise ValueError(f"Invalid wind bearing: {bearing}")

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
        super().__init__(f"Unable to find location {location!r}")
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


@hook.on_start()
def create_owm_api(bot):
    owm_key = bot.config.get_api_key("openweathermap")
    if owm_key:
        data.owm_api = OWM(owm_key, pyowm.owm.cfg.get_default_config())
    else:
        data.owm_api = None


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
    if not data.maps_api:
        return (
            None,
            "This command requires a Google Developers Console API key.",
        )

    if not data.owm_api:
        return (
            None,
            "This command requires a OpenWeatherMap API key.",
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

    owm_api = data.owm_api
    wm = owm_api.weather_manager()
    conditions = wm.one_call(
        location_data["lat"], location_data["lng"], exclude="minutely,hourly"
    )

    return (location_data, conditions), None


@hook.command("weather", "we", autohelp=False)
def weather(reply, db, triggered_prefix, event):
    """<location> - Gets weather data for <location>."""
    res, err = check_and_parse(event, db)
    if not res:
        return err

    location_data, owm = res
    daily_conditions: List[Weather] = owm.forecast_daily
    current: Weather = owm.current
    today = daily_conditions[0]
    wind_mph = current.wind("miles_hour")
    wind_speed = wind_mph["speed"]
    today_temp = today.temperature("fahrenheit")
    today_high = today_temp["max"]
    today_low = today_temp["min"]
    current_temperature = current.temperature("fahrenheit")["temp"]
    current_data = {
        "name": "Current",
        "wind_direction": bearing_to_card(wind_mph["deg"]),
        "wind_speed_mph": wind_speed,
        "wind_speed_kph": mph_to_kph(wind_speed),
        "summary": current.status,
        "temp_f": round_temp(current_temperature),
        "temp_c": round_temp(convert_f2c(current_temperature)),
        "temp_high_f": round_temp(today_high),
        "temp_high_c": round_temp(convert_f2c(today_high)),
        "temp_low_f": round_temp(today_low),
        "temp_low_c": round_temp(convert_f2c(today_low)),
        "humidity": current.humidity / 100,
    }

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
        colors.parse(f"$(b){part[0]}$(b): {part[1]}$(clear)") for part in parts
    )

    reply(
        colors.parse(
            "{current_str} -- "
            "{place} - "
            "($(i)To get a forecast, use {cmd_prefix}fc$(i))"
        ).format(
            place=location_data["address"],
            current_str=current_str.format_map(current_data),
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

    location_data, owm = res

    one_call = owm
    daily_conditions = one_call.forecast_daily
    today, tomorrow, *three_days = daily_conditions[:5]

    today_data = {
        "data": today,
    }
    tomorrow_data = {"data": tomorrow}
    three_days_data = [{"data": d} for d in three_days]
    today_data["name"] = "Today"
    tomorrow_data["name"] = "Tomorrow"

    for day_fc in (today_data, tomorrow_data):
        wind_speed = day_fc["data"].wind("miles_hour")
        day_fc.update(
            wind_direction=bearing_to_card(wind_speed["deg"]),
            wind_speed_mph=wind_speed["speed"],
            wind_speed_kph=mph_to_kph(wind_speed["speed"]),
            summary=day_fc["data"].status,
        )

    for fc_data in (today_data, tomorrow_data, *three_days_data):
        temp = fc_data["data"].temperature("fahrenheit")
        high = temp["max"]
        low = temp["min"]
        fc_data.update(
            temp_high_f=round_temp(high),
            temp_high_c=round_temp(convert_f2c(high)),
            temp_low_f=round_temp(low),
            temp_low_c=round_temp(convert_f2c(low)),
            humidity=fc_data["data"].humidity / 100,
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
        f"{part[0]}: {part[1]}" for part in parts
    )

    out_format = "{today_str} | {tomorrow_str} -- {place}"

    reply(
        colors.parse(out_format).format(
            today_str=day_str.format_map(today_data),
            tomorrow_str=day_str.format_map(tomorrow_data),
            place=location_data["address"],
        )
    )
    return None
