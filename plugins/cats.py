import requests
from requests import HTTPError

from cloudbot import hook


def get_data(url, reply, bot, params=None):
    try:
        with requests.get(
            url, headers={"User-Agent": bot.user_agent}, params=params
        ) as r:
            r.raise_for_status()
    except HTTPError:
        reply("API error occurred.")
        raise

    return r


@hook.command(autohelp=False)
def cats(reply, bot):
    """- gets a fucking fact about cats."""
    r = get_data(
        "https://catfact.ninja/fact", reply, bot, params={"max_length": 100}
    )
    json = r.json()
    response = json["fact"]
    return response


@hook.command(autohelp=False)
def catgifs(reply, bot):
    """- gets a fucking cat gif."""
    r = get_data("http://marume.herokuapp.com/random.gif", reply, bot)
    return "OMG A CAT GIF: {}".format(r.url)
