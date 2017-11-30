import requests
from requests import HTTPError

from cloudbot import hook


def get_data(url, reply, bot):
    try:
        r = requests.get(url, headers={'User-Agent': bot.user_agent})
        r.raise_for_status()
    except HTTPError:
        reply("API error occurred.")
        raise

    return r


@hook.command(autohelp=False)
def cats(reply, bot):
    """gets a fucking fact about cats."""
    r = get_data('http://catfacts-api.appspot.com/api/facts?number=1', reply, bot)
    json = r.json()
    response = json['facts']
    return response


@hook.command(autohelp=False)
def catgifs(reply, bot):
    """gets a fucking cat gif."""
    r = get_data("http://marume.herokuapp.com/random.gif", reply, bot)
    return "OMG A CAT GIF: {}".format(r.url)
