"""
google.py

Originally for RoboCop 2, a replacement after Google's deprecation of Google Web Search API
Module requires a Google Custom Search API key and a Custom Search Engine ID in order to function.

Created By:
    - Foxlet <https://furcode.tk/>

License:
    GNU General Public License (Version 3)
"""

import requests

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util import filesize, formatting

API_CS = "https://www.googleapis.com/customsearch/v1"


@hook.command("gse")
def gse(text):
    """<query> - Returns first Google search result for <query>."""
    dev_key = bot.config.get_api_key("google_dev_key")
    cx = bot.config.get_api_key("google_cse_id")
    if not dev_key:
        return "This command requires a Google Developers Console API key."
    if not cx:
        return "This command requires a custom Google Search Engine ID."

    parsed = requests.get(
        API_CS, params={"cx": cx, "q": text, "key": dev_key}
    ).json()

    try:
        result = parsed["items"][0]
    except KeyError:
        return "No results found."

    title = formatting.truncate_str(result["title"], 60)
    content = result["snippet"]

    if not content:
        content = "No description available."
    else:
        content = formatting.truncate_str(content.replace("\n", ""), 150)

    return '{} -- \x02{}\x02: "{}"'.format(result["link"], title, content)


@hook.command("gseis", "image")
def gse_gis(text):
    """<query> - Returns first Google Images result for <query>."""
    dev_key = bot.config.get_api_key("google_dev_key")
    cx = bot.config.get_api_key("google_cse_id")
    if not dev_key:
        return "This command requires a Google Developers Console API key."
    if not cx:
        return "This command requires a custom Google Search Engine ID."

    parsed = requests.get(
        API_CS,
        params={"cx": cx, "q": text, "searchType": "image", "key": dev_key},
    ).json()

    try:
        result = parsed["items"][0]
        metadata = parsed["items"][0]["image"]
    except KeyError:
        return "No results found."

    dimens = "{}x{}px".format(metadata["width"], metadata["height"])
    size = filesize.size(int(metadata["byteSize"]))

    return "{} [{}, {}, {}]".format(
        result["link"], dimens, result["mime"], size
    )
