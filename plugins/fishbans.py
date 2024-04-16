from urllib.parse import quote_plus

import requests
import requests.exceptions

from cloudbot import hook
from cloudbot.util import formatting

api_url = "http://api.fishbans.com/stats/{}/"


@hook.command("bans", "fishbans")
def fishbans(text, bot):
    """<user> - gets information on <user>'s minecraft bans from fishbans"""
    user = text.strip()
    headers = {"User-Agent": bot.user_agent}

    try:
        request = requests.get(
            api_url.format(quote_plus(user)), headers=headers
        )
        request.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        return f"Could not fetch ban data from the Fishbans API: {e}"

    try:
        json = request.json()
    except ValueError:
        return (
            "Could not fetch ban data from the Fishbans API: Invalid Response"
        )

    if not json["success"]:
        return f"Could not fetch ban data for {user}."

    user_url = f"http://fishbans.com/u/{user}/"
    ban_count = json["stats"]["totalbans"]

    if ban_count == 1:
        return f"The user \x02{user}\x02 has \x021\x02 ban - {user_url}"
    elif ban_count > 1:
        return (
            f"The user \x02{user}\x02 has \x02{ban_count}\x02 bans - {user_url}"
        )
    else:
        return f"The user \x02{user}\x02 has no bans - {user_url}"


@hook.command()
def bancount(text, bot):
    """<user> - gets a count of <user>'s minecraft bans from fishbans"""
    user = text.strip()
    headers = {"User-Agent": bot.user_agent}

    try:
        request = requests.get(
            api_url.format(quote_plus(user)), headers=headers
        )
        request.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        return f"Could not fetch ban data from the Fishbans API: {e}"

    try:
        json = request.json()
    except ValueError:
        return (
            "Could not fetch ban data from the Fishbans API: Invalid Response"
        )

    if not json["success"]:
        return f"Could not fetch ban data for {user}."

    user_url = f"http://fishbans.com/u/{user}/"
    services = json["stats"]["service"]

    out = []
    for service, ban_count in list(services.items()):
        if ban_count != 0:
            out.append(f"{service}: \x02{ban_count}\x02")
        else:
            pass

    if not out:
        return f"The user \x02{user}\x02 has no bans - {user_url}"
    else:
        return "Bans for \x02{}\x02: {} - {}".format(
            user, formatting.get_text_list(out, "and"), user_url
        )
