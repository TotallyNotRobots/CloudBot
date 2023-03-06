"""
octopart.py

Search for electronic parts using the Octopart API.

Created By:
    - foxlet <https://github.com/foxlet>

Modified By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""

import requests

from cloudbot import hook
from cloudbot.bot import bot

API_URL = "https://octopart.com/api/v3/parts/search"


@hook.command("octopart", "octo")
def octopart(text, reply):
    """<keyword> - Search for any part on the Octopart database."""
    api_key = bot.config.get_api_key("octopart")
    if not api_key:
        return "Octopart API key required."

    params = {"apikey": api_key, "q": text, "start": 0, "limit": 1}

    try:
        request = requests.get(API_URL, params=params)
        request.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        reply("Could not fetch part data: {}".format(e))
        raise

    response = request.json()

    if not response["results"]:
        return "No results."

    # get part
    results = response["results"]

    for result in results:
        part = result["item"]

        # print matched part
        reply(
            "{} - {} - {}".format(
                part["brand"]["name"], part["mpn"], part["octopart_url"]
            )
        )

    return None
