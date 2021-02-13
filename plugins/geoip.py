import gzip
import logging
import shutil
import socket
import time

import geoip2.database
import geoip2.errors
import requests

from cloudbot import hook
from cloudbot.bot import CloudBot
from cloudbot.util import async_util

logger = logging.getLogger("cloudbot")

DB_URL = (
    "http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz"
)
PATH = "GeoLite2-City.mmdb"


def get_path(bot: CloudBot):
    return bot.data_path / PATH


class GeoipReader:
    def __init__(self):
        self.reader = None


geoip_reader = GeoipReader()


def fetch_db(path):
    path.unlink(missing_ok=True)

    with requests.get(DB_URL, stream=True) as r:
        if r.status_code != 200:
            return

        with gzip.open(r.raw) as infile:
            with path.open("wb") as outfile:
                shutil.copyfileobj(infile, outfile)


def update_db(bot: CloudBot):
    """
    Updates the DB.
    """
    path = get_path(bot)
    if (not path.is_file()) or (time.time() - path.stat().st_mtime) > (
        14 * 24 * 60 * 60
    ):
        fetch_db(path)

    try:
        return geoip2.database.Reader(path)
    except geoip2.errors.GeoIP2Error:
        # issue loading, geo
        fetch_db(path)
        return geoip2.database.Reader(path)


async def check_db(loop, bot):
    """
    runs update_db in an executor thread and sets geoip_reader to the result
    if this is run while update_db is already executing bad things will happen
    """
    if not geoip_reader.reader:
        logger.info("Loading GeoIP database")
        db = await loop.run_in_executor(None, update_db, bot)
        logger.info("Loaded GeoIP database")
        geoip_reader.reader = db


@hook.on_start()
async def load_geoip(loop, bot):
    async_util.wrap_future(check_db(loop, bot), loop=loop)


@hook.command()
async def geoip(text, reply, loop):
    """<host|ip> - Looks up the physical location of <host|ip> using Maxmind GeoLite """
    if not geoip_reader.reader:
        return "GeoIP database is still loading, please wait a minute"

    try:
        ip = await loop.run_in_executor(None, socket.gethostbyname, text)
    except socket.gaierror:
        return "Invalid input."

    try:
        location_data = await loop.run_in_executor(
            None, geoip_reader.reader.city, ip
        )
    except geoip2.errors.AddressNotFoundError:
        return "Sorry, I can't locate that in my database."

    data = {
        "cc": location_data.country.iso_code or "N/A",
        "country": location_data.country.name or "Unknown",
        "city": location_data.city.name or "Unknown",
    }

    # add a region to the city if one is listed
    if location_data.subdivisions.most_specific.name:
        data["city"] += ", " + location_data.subdivisions.most_specific.name

    reply(
        "\x02Country:\x02 {country} ({cc}), \x02City:\x02 {city}".format(**data)
    )
