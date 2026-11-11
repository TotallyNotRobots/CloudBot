from __future__ import annotations

import datetime as dt
import re
import time
from typing import TYPE_CHECKING

import requests

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot

# Define some constants
base_url = "https://maps.googleapis.com/maps/api/"
geocode_api = f"{base_url}geocode/json"
timezone_api = f"{base_url}timezone/json"


def check_status(status, api):
    """A little helper function that checks an API error code and returns a nice message.
    Returns None if no errors found"""
    if status == "REQUEST_DENIED":
        return f"The {api} API is off in the Google Developers Console."

    if status == "ZERO_RESULTS":
        return "No results found."

    if status == "OVER_QUERY_LIMIT":
        return f"The {api} API quota has run out."

    if status == "UNKNOWN_ERROR":
        return "Unknown Error."

    if status == "INVALID_REQUEST":
        return "Invalid Request."

    if status == "OK":
        return None

    # !!!
    return "Unknown Demons."


@hook.command("time")
def time_command(text: str, reply, bot: CloudBot) -> str:
    """<location> - Gets the current time in <location>."""
    dev_key = bot.config.get_api_key("google_dev_key")
    if not dev_key:
        return "This command requires a Google Developers Console API key."

    if text.lower().startswith(("utc", "gmt")):
        timezone = text.strip()
        pattern = re.compile(r"utc|gmt|[:+]")
        utcoffset = [x for x in pattern.split(text.lower()) if x]
        if len(utcoffset) > 2:
            return "Please specify a valid UTC/GMT format Example: UTC-4, UTC+7 GMT7"

        if len(utcoffset) == 1:
            utcoffset.append("0")

        if len(utcoffset) == 2:
            try:
                offset = dt.timedelta(
                    hours=int(utcoffset[0]), minutes=int(utcoffset[1])
                )
            except Exception:
                reply(
                    "Sorry I could not parse the UTC format you entered. Example UTC7 or UTC-4"
                )
                raise

            curtime = dt.datetime.now(dt.timezone.utc)
            tztime = curtime + offset
            formatted_time = dt.datetime.strftime(
                tztime, "%I:%M %p, %A, %B %d, %Y"
            )
            return f"\x02{formatted_time}\x02 ({timezone})"

    # Use the Geocoding API to get coordinates from the input
    params = {"address": text, "key": dev_key}
    if (bias := bot.config.get("location_bias_cc")) is not None:
        params["region"] = bias

    json = requests.get(geocode_api, params=params).json()

    error = check_status(json["status"], "geocoding")
    if error:
        return error

    result = json["results"][0]

    location_name = result["formatted_address"]
    location = result["geometry"]["location"]

    # Now we have the coordinates, we use the Timezone API to get the timezone
    formatted_location = "{lat},{lng}".format_map(location)

    epoch = time.time()

    params = {
        "location": formatted_location,
        "timestamp": str(epoch),
        "key": dev_key,
    }

    json = requests.get(timezone_api, params=params).json()

    error = check_status(json["status"], "timezone")
    if error:
        return error

    # Work out the current time
    tz_offset = json["rawOffset"] + json["dstOffset"]

    # I'm telling the time module to parse the data as GMT, but whatever, it doesn't matter
    # what the time module thinks the timezone is. I just need dumb time formatting here.
    raw_time = time.gmtime(epoch + tz_offset)
    formatted_time = time.strftime("%I:%M %p, %A, %B %d, %Y", raw_time)

    timezone = json["timeZoneName"]

    return f"\x02{formatted_time}\x02 - {location_name} ({timezone})"


@hook.command(autohelp=False)
def beats(text) -> str:
    """- Gets the current time in .beats (Swatch Internet Time)."""

    if text.lower() == "wut":
        return (
            "Instead of hours and minutes, the mean solar day is divided "
            'up into 1000 parts called ".beats". Each .beat lasts 1 minute and'
            " 26.4 seconds. Times are notated as a 3-digit number out of 1000 af"
            "ter midnight. So, @248 would indicate a time 248 .beats after midni"
            "ght representing 248/1000 of a day, just over 5 hours and 57 minute"
            "s. There are no timezones."
        )

    if text.lower() == "guide":
        return "1 day = 1000 .beats, 1 hour = 41.666 .beats, 1 min = 0.6944 .beats, 1 second = 0.01157 .beats"

    t = time.gmtime()
    h, m, s = t.tm_hour, t.tm_min, t.tm_sec

    utc = 3600 * h + 60 * m + s
    bmt = utc + 3600  # Biel Mean Time (BMT)

    beat = bmt / 86.4

    if beat > 1000:
        beat -= 1000

    return f"Swatch Internet Time: @{beat:06.2f}"
