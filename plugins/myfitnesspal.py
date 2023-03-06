import locale
import math
from typing import Dict, List

import requests
from requests import HTTPError

from cloudbot import hook
from cloudbot.util.http import parse_soup

scrape_url = "https://www.myfitnesspal.com/food/diary/{}"


@hook.command("mfp", "myfitnesspal")
def mfp(text, reply):
    """<user> - returns macros from the MyFitnessPal food diary of <user>"""
    request = requests.get(scrape_url.format(text))

    try:
        request.raise_for_status()
    except HTTPError as e:
        reply("Failed to fetch info ({})".format(e.response.status_code))
        raise

    if request.status_code != requests.codes.ok:
        return "Failed to fetch info ({})".format(request.status_code)

    output = "Diary for {}: ".format(text)

    try:
        soup = parse_soup(request.text)

        title = soup.find("h1", {"class": "main-title"})
        if title:
            if title.text == "This Food Diary is Private":
                return "{}'s food diary is private.".format(text)
            if title.text == "This Username is Invalid":
                return "User {} does not exist.".format(text)

        # the output of table depends on the user's MFP profile configuration
        headers = get_headers(soup)
        totals = get_values(soup, "total")
        remaining = get_values(soup, "alt")

        for idx, val in enumerate(headers["captions"]):
            kwargs = {
                "caption": val,
                "total": totals[idx],
                "remain": remaining[idx],
                "units": headers["units"][idx],
                "pct": math.floor((totals[idx] / remaining[idx]) * 100),
            }

            output += "{caption}: {total}/{remain}{units} ({pct}%) ".format(
                **kwargs
            )

        output += " ({})".format(scrape_url.format(text))

    except Exception:
        reply("Error parsing results.")
        raise

    return output


def get_headers(soup):
    """get nutrient headers from the soup"""
    headers: Dict[str, List[str]] = {"captions": [], "units": []}

    footer = soup.find("tfoot")
    for cell in footer.findAll("td", {"class": "nutrient-column"}):
        div = cell.find("div")
        headers["units"].append(div.text)
        headers["captions"].append(div.previous_sibling.strip())

    return headers


def get_values(soup, row_class):
    """get values from a specific summary row based on the row class"""
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")  # for number parsing

    values = []

    cells = soup.find("tr", {"class": row_class}).find_all("td")

    for elem in cells[1:]:
        # if there's a child span with class "macro-value", use its value
        # otherwise use the cell text
        span = elem.find("span", {"class": "macro-value"})
        if span:
            value = span.text
        else:
            value = elem.text

        if value.strip() != "":
            values.append(locale.atoi(value))

    return values
