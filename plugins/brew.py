import requests
from requests import HTTPError

from cloudbot import hook
from cloudbot.bot import bot

api_url = "http://api.brewerydb.com/v2/search?format=json"


@hook.command("brew")
def brew(text, reply):
    """<query> - returns the first brewerydb search result for <query>"""
    api_key = bot.config.get_api_key("brewerydb")
    if not api_key:
        return "No brewerydb API key set."

    params = {"key": api_key, "type": "beer", "withBreweries": "Y", "q": text}
    request = requests.get(api_url, params=params)

    try:
        request.raise_for_status()
    except HTTPError:
        reply("Failed to fetch info ({})".format(request.status_code))
        raise

    response = request.json()

    output = "No results found."

    try:
        if "totalResults" in response:
            if response["totalResults"] == 0:
                return output

            beer = response["data"][0]
            brewery = beer["breweries"][0]

            style = "unknown style"
            if "style" in beer:
                style = beer["style"]["shortName"]

            abv = "?.?"
            if "abv" in beer:
                abv = beer["abv"]

            url = "[no website found]"
            if "website" in brewery:
                url = brewery["website"]

            content = {
                "name": beer["nameDisplay"],
                "style": style,
                "abv": abv,
                "brewer": brewery["name"],
                "url": url,
            }

            output = "{name} by {brewer} ({style}, {abv}% ABV) - {url}".format(
                **content
            )

    except Exception:
        reply("Error parsing results.")
        raise

    return output
