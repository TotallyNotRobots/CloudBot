"""
issafe.py

Check the Google Safe Browsing list to see a website's safety rating.

Created By:
    - Foxlet <https://furcode.tk/>

License:
    GNU General Public License (Version 3)
"""

from urllib.parse import urlparse

import requests

import cloudbot
from cloudbot import hook
from cloudbot.bot import bot

API_SB = "https://sb-ssl.google.com/safebrowsing/api/lookup"


@hook.command()
def issafe(text):
    """<website> - Checks the website against Google's Safe Browsing List."""
    if urlparse(text).scheme not in ["https", "http"]:
        return "Check your URL (it should be a complete URI)."

    dev_key = bot.config.get_api_key("google_dev_key")
    parsed = requests.get(
        API_SB,
        params={
            "url": text,
            "client": "cloudbot",
            "key": dev_key,
            "pver": "3.1",
            "appver": str(cloudbot.__version__),
        },
    )
    parsed.raise_for_status()

    if parsed.status_code == 204:
        condition = "\x02{}\x02 is safe.".format(text)
    else:
        condition = "\x02{}\x02 is known to contain: {}".format(
            text, parsed.text
        )
    return condition
