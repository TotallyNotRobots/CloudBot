import re
import urllib
import urllib.parse
import uuid

import requests

from cloudbot import hook

HIST_API = "http://api.fishbans.com/history/{}"
UUID_API = "http://api.goender.net/api/uuids/{}/"


def get_name(user_uuid):
    # submit the profile request
    request = requests.get(UUID_API.format(user_uuid))
    request.raise_for_status()
    data = request.json()
    return data[user_uuid]


@hook.command("mcuser", "mcpaid", "haspaid")
def mcuser(text, bot, reply):
    """<username> - gets information about the Minecraft user <account>"""
    headers = {"User-Agent": bot.user_agent}
    text = text.strip()

    # check if we are looking up a UUID
    cleaned = text.replace("-", "")
    if re.search(r"^[0-9a-f]{32}$", cleaned, re.I):
        # we are looking up a UUID, get a name.
        try:
            name = get_name(cleaned)
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            KeyError,
        ) as e:
            reply("Could not get username from UUID: {}".format(e))
            raise
    else:
        name = text

    # get user data from fishbans
    try:
        request = requests.get(
            HIST_API.format(urllib.parse.quote(name)), headers=headers
        )
        request.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        reply("Could not get profile status: {}".format(e))
        raise

    # read the fishbans data
    try:
        results = request.json()
    except ValueError:
        return "Could not parse profile status"

    # check for errors from fishbans and handle them
    if not results["success"]:
        if results["error"] == "User is not premium.":
            return "The account \x02{}\x02 is not premium or does not exist.".format(
                text
            )

        return results["error"]

    username = results["data"]["username"]
    uid = uuid.UUID(results["data"]["uuid"])

    return (
        "The account \x02{}\x02 ({}) exists. It is a \x02paid\x02"
        " account.".format(username, uid)
    )
