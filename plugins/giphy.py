import random

import requests

from cloudbot import hook

api_url = "https://api.giphy.com/v1/gifs"


@hook.command("gif", "giphy")
def giphy(text, bot):
    """<query> - Searches giphy.com for a gif using the provided search term."""
    api_key = bot.config.get_api_key("giphy")
    term = text.strip()
    search_url = api_url + "/search"
    params = {"q": term, "limit": 10, "fmt": "json", "api_key": api_key}
    results = requests.get(search_url, params=params)
    results.raise_for_status()
    r = results.json()
    if not r["data"]:
        return "no results found."

    gif = random.choice(r["data"])
    if gif["rating"]:
        out = "{} content rating: \x02{}\x02. (Powered by GIPHY)".format(
            gif["embed_url"], gif["rating"].upper()
        )
    else:
        out = "{} - (Powered by GIPHY)".format(gif["embed_url"])

    return out
