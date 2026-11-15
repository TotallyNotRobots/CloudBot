from __future__ import annotations

import re
from typing import TYPE_CHECKING

import requests

from cloudbot import hook
from cloudbot.util import formatting, web
from cloudbot.util.http import parse_soup

if TYPE_CHECKING:
    from cloudbot.event_functions import EventReply

# CONSTANTS
steam_re = re.compile(r".*://store.steampowered.com/app/([0-9]+)?.*", re.I)

API_URL = "http://store.steampowered.com/api/appdetails/"
STORE_URL = "http://store.steampowered.com/app/{}/"


# OTHER FUNCTIONS


def format_game(app_id, show_url=True):
    """
    Takes a Steam Store app ID and returns a formatted string with data about that app ID
    """
    params = {"appids": app_id}

    try:
        request = requests.get(API_URL, params=params, timeout=15)
        request.raise_for_status()
    except requests.RequestException as e:
        return f"Could not get game info: {e}"

    data = request.json()
    game = data[app_id]["data"]

    # basic info
    out = [f"\x02{game['name']}\x02"]

    desc = " ".join(formatting.strip_html(game["about_the_game"]).split())
    out.append(formatting.truncate(desc, 75))

    # genres
    try:
        genres = ", ".join([g["description"] for g in game["genres"]])
        out.append(f"\x02{genres}\x02")
    except KeyError:
        # some things have no genre
        pass

    # release date
    if game["release_date"]["coming_soon"]:
        out.append(f"coming \x02{game['release_date']['date']}\x02")
    else:
        out.append(f"released \x02{game['release_date']['date']}\x02")

    # pricing
    if game["is_free"]:
        out.append("\x02free\x02")
    elif not game.get("price_overview"):
        # game has no pricing, it's probably not released yet
        pass
    else:
        price = game["price_overview"]

        # the steam API sends prices as an int like "9999" for $19.99, we divmod to get the actual price
        if price["final"] == price["initial"]:
            dollars, cents = divmod(price["final"], 100)
            out.append(f"\x02${int(dollars)}.{int(cents):02}\x02")
        else:
            dollars, cents = divmod(price["final"], 100)
            price_now = f"${int(dollars)}.{int(cents):02}"
            original_dollars, original_cents = divmod(price["initial"], 100)
            price_original = (
                f"${int(original_dollars)}.{int(original_cents):02}"
            )

            out.append(f"\x02{price_now}\x02 (was \x02{price_original}\x02)")

    if show_url:
        url = web.try_shorten(STORE_URL.format(game["steam_appid"]))
        out.append(url)

    return " - ".join(out)


# HOOK FUNCTIONS


@hook.command()
def steam(text, reply: EventReply):
    """<query> - Search for specified game/trailer/DLC"""
    params = {"term": text.strip().lower()}

    try:
        request = requests.get(
            "http://store.steampowered.com/search/", params=params
        )
        request.raise_for_status()
    except requests.RequestException as e:
        reply(f"Could not get game info: {e}")
        raise

    soup = parse_soup(request.text, from_encoding="utf-8")
    result = soup.find("a", {"class": "search_result_row"})

    if not result:
        return "No game found."

    app_id = result["data-ds-appid"]
    return format_game(app_id)


@hook.regex(steam_re)
def steam_url(match):
    app_id = match.group(1)
    return format_game(app_id, show_url=False)
