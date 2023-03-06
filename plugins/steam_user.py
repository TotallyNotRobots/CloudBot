from typing import Dict

import requests

from cloudbot import hook
from cloudbot.util import formatting
from cloudbot.util.http import parse_xml

API_URL = "https://steamcommunity.com/id/{}/"
ID_BASE = 76561197960265728

headers: Dict[str, str] = {}


class SteamError(Exception):
    pass


def convert_id32(id_64):
    """
    Takes a Steam ID_64 formatted ID and returns a ID_32 formatted ID
    """
    out = ["STEAM_0:"]
    final = id_64 - ID_BASE
    if final % 2 == 0:
        out.append("0:")
    else:
        out.append("1:")
    out.append(str(final // 2))
    return "".join(out)


def convert_id3(id_64):
    """
    Takes a Steam ID_64 formatted ID and returns a ID_3 formatted ID
    """
    _id = (id_64 - ID_BASE) * 2
    if _id % 2 == 0:
        _id += 0
    else:
        _id += 1
    actual = str(_id // 2)
    return "U:1:{}".format(actual)


def get_data(user):
    """
    Takes a Steam Community ID of a Steam user and returns a dict of data about that user
    """
    data = {}

    # form the request
    params = {"xml": 1}

    # get the page
    try:
        request = requests.get(
            API_URL.format(user), params=params, headers=headers
        )
        request.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        raise SteamError("Could not get user info: {}".format(e)) from e

    profile = parse_xml(request.content)

    try:
        data["name"] = profile.find("steamID").text
        data["id_64"] = int(profile.find("steamID64").text)
        online_state = profile.find("stateMessage").text
    except AttributeError as e:
        raise SteamError("Could not get data for this user.") from e

    # will make this pretty later
    online_state = online_state.replace("<br/>", ": ")
    data["state"] = formatting.strip_html(online_state)

    data["id_32"] = convert_id32(data["id_64"])
    data["id_3"] = convert_id3(data["id_64"])

    return data


@hook.on_start()
def set_headers(bot):
    """Runs on initial plugin load and sets the HTTP headers for this plugin."""
    headers["User-Agent"] = bot.user_agent


@hook.command("steamid", "sid", "steamuser", "su")
def steamid(text, reply):
    """<username> - gets the steam ID of <username>. Uses steamcommunity.com/id/<nickname>."""

    try:
        data = get_data(text)
    except SteamError as e:
        reply("{}".format(e))
        raise

    return "{name} ({state}): \x02ID64:\x02 {id_64}, \x02ID32:\x02 {id_32}, \x02ID3:\x02 {id_3}".format(
        **data
    )
