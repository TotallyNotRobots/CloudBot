from __future__ import annotations

import re
from typing import TYPE_CHECKING

import requests
from requests import HTTPError

from cloudbot import hook
from cloudbot.util.http import parse_soup
from cloudbot.util.timeparse import time_parse

if TYPE_CHECKING:
    from cloudbot.event_functions import EventReply

search_url = "http://dragonvale.wikia.com/api/v1/Search/list"

egg_calc_url = "http://www.dragonvalebreedingguide.com/dragonvale-calculator"


def striphtml(data):
    string = re.compile(r"<.*?>")
    return string.sub("", data)


@hook.command("dragon", "ds")
def dragonsearch(text, reply: EventReply) -> str:
    """<query> - Searches the dragonvale wiki for the specified text."""
    params = {"query": text.strip(), "limit": 1}

    r = requests.get(search_url, params=params)

    try:
        r.raise_for_status()
    except HTTPError:
        reply(f"The API returned error code {r.status_code}.")
        raise

    if not r.status_code == 200:
        return f"The API returned error code {r.status_code}."

    data = r.json()["items"][0]
    return f"\x02{data['title']}\x02 -- {striphtml(data['snippet']).split('&hellip;')[0].strip()}: {data['url']}"


@hook.command("eggcalc", "dragoncalc", "dc")
def egg_calculator(text):
    """<time> - Parses dragonvalebreedingguide.com for a list of possible dragons based on the incubation time.
    Enter the time as 5 hours, 30 minutes. For upgraded incubation times put 'upgrade' at the front of the time length
    """
    params: dict[str, int | float] = {"avail": 1}
    if text.lower().startswith("upgrade"):
        timer = text.replace("upgrade", "")
        time2 = time_parse(timer.strip())
        if not time2:
            return "invalid time format"

        params["time2"] = time2
    else:
        timer = text
        time = time_parse(timer.strip())
        if not time:
            return "invalid time format"

        params["time"] = time

    r = requests.get(egg_calc_url, params=params, timeout=5)
    soup = parse_soup(r.text)
    dragons = []
    for line in soup.find_all("td", {"class": "views-field views-field-title"}):
        dragons.append(line.text.replace("\n", "").strip())

    return ", ".join(dragons)
