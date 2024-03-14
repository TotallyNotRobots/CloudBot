import requests
from requests import HTTPError

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util import web

#
api_url = "https://api.lyricsnmusic.com/songs"


@hook.command("lyrics")
def lyricsnmusic(text, reply):
    """<artist and/or song> - will fetch the first 150 characters of a song and a link to the full lyrics."""
    api_key = bot.config.get_api_key("lyricsnmusic")
    params = {"api_key": api_key, "q": text}
    r = requests.get(api_url, params=params)
    try:
        r.raise_for_status()
    except HTTPError:
        reply("There was an error returned by the LyricsNMusic API.")
        raise

    if r.status_code != 200:
        return "There was an error returned by the LyricsNMusic API."
    json = r.json()
    data = json[0]
    snippet = data["snippet"].replace("\r\n", " ")
    url = web.try_shorten(data["url"])
    title = data["title"]
    viewable = data["viewable"]
    out = "\x02{}\x02 -- {} {}".format(title, snippet, url)
    if not viewable:
        out += " Full lyrics not available."
    return out
