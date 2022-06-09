import re

from cloudbot import hook
import requests
from thefuzz import fuzz

API = "https://blackbeardapi.herokuapp.com/"


def getJson(path, params={}):
    r = requests.get(API + path, params=params)
    return r.json()


providers = {}

@hook.on_start
def load_providers():
    global providers
    providers = getJson("providers")["providers"]
    providers = [prov["Name"] for prov in providers]


@hook.command("blackbeard", "blb")
def blackbeard(text, reply):
    """<provider> <search> -N - searches for <search> on <provider>. If -N is provided, where N is a number
    , will return the Nth episode"""
    args = text.strip().split()
    if len(args) < 2:
        return "Usage: .blackbeard <provider> <search>"

    m = re.match(r"^-(\d+)$", args[-1].strip().casefold())
    episode = None
    if m:
        episode = int(m.group(1)) - 1
        args = args[:-1]

    provider = args[0]
    search = " ".join(args[1:])
    if provider not in providers:
        return "Invalid provider. Valid providers are: " + ", ".join(providers)

    results = getJson("search", {"provider": provider, "q": search})
    if "error" in results:
        return results["message"]

    shows = results["shows"]
    # Find show which the title has the bigger fuzzy ratio with search
    show = max(shows, key=lambda show: fuzz.ratio(
        show["Title"].strip().casefold(), search.strip().casefold()))

    reply("Show: " + show["Title"] + " - " + show["Url"])
    if episode is None:
        reply("Description: " + show["Metadata"]["Description"][:454])
        return

    episodes = getJson("episodes", {"provider": provider, "showurl": show["Url"]})
    if "error" in episodes:
        return episodes["message"]

    if episode > len(episodes):
        return "Invalid episode number. Max episode is " + str(len(episodes))

    episode = episodes["episodes"][episode]
    reply(episode["Title"] + " - " + episode["Url"])
    reply("Description: " + episode["Metadata"]["Description"][:454])
