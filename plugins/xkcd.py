import datetime as dt
import re

import requests
from yarl import URL

from cloudbot import hook
from cloudbot.util.http import parse_soup

xkcd_re = re.compile(r"(.*:)//(www.xkcd.com|xkcd.com)(.*)", re.I)

XKCD_URL = URL("http://www.xkcd.com/")
ONR_URL = URL("http://www.ohnorobot.com/")


def xkcd_info(xkcd_id, url=False) -> str:
    """takes an XKCD entry ID and returns a formatted string"""
    request = requests.get(str(XKCD_URL / xkcd_id / "info.0.json"))
    request.raise_for_status()
    data = request.json()

    date = dt.date(
        year=int(data["year"]), month=int(data["month"]), day=int(data["day"])
    )
    date_str = date.strftime("%d %B %Y")

    if url:
        url = f" | {XKCD_URL / xkcd_id.replace('/', '')}"
    else:
        url = ""

    return f"xkcd: \x02{data['title']}\x02 ({date_str}){url}"


def xkcd_search(term):
    params = {
        "s": term,
        "Search": "Search",
        "comic": 56,
        "e": 0,
        "n": 0,
        "b": 0,
        "m": 0,
        "d": 0,
        "t": 0,
    }
    request = requests.get(str(ONR_URL), params=params)
    request.raise_for_status()
    soup = parse_soup(request.text)
    result = soup.find("li")
    if not result:
        return "No results found!"

    tinylink = result.find("div", {"class": "tinylink"})
    if tinylink is None:
        raise ValueError("Can't find tinylink in page")

    xkcd_id = tinylink.get_text()[:-1].split("/")[-1]
    return xkcd_info(xkcd_id, url=True)


@hook.regex(xkcd_re)
def xkcd_url(match):
    xkcd_id = match.group(3).split(" ")[0].split("/")[1]
    return xkcd_info(xkcd_id)


@hook.command()
def xkcd(text):
    """<search term> - Search for xkcd comic matching <search term>"""
    return xkcd_search(text)
