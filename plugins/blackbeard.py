import re

import requests
from thefuzz import fuzz

from cloudbot import hook

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

def search_show(provider, search):
    results = getJson("search", {"provider": provider, "q": search})
    if "error" in results:
        return results["message"], False

    shows = results["shows"]
    if shows is None or len(shows) == 0:
        return None, True
    # Find show which the title has the bigger fuzzy ratio with search
    return max(shows, key=lambda show: fuzz.ratio(
        show["Title"].strip().casefold(), search.strip().casefold())), True


@hook.command("blackbeard", "blb")
def blackbeard(text, reply):
    """
    [provider] <search> -N - searches for <search> on <provider>. If -N is provided, where N is a number
    , will return the Nth episode. You can also use `list` to list providers
    """
    global providers
    args = text.strip().split()
    if len(args) < 1:
        return "Usage: .blackbeard [provider] <search> or .blackbeard list"

    m = re.match(r"^-(\d+)$", args[-1].strip().casefold())
    episode = None
    if m:
        episode = int(m.group(1)) - 1
        args = args[:-1]

    provider = args[0]
    search = " ".join(args[1:])
    if provider == "list" and len(args) == 1:
        return "Available providers: " + ", ".join(providers)

    if provider not in providers:
        search = provider + " " + search
        provider = None

    shows = []
    if provider is None:
        for prov in providers:
            show, ok = search_show(prov, search)
            if not ok:
                return show
            if show is None:
                continue
            shows.append({**show, **{"provider": prov}})
    else:
        show, ok = search_show(provider, search)
        if not ok:
            return show
        shows.append({**show, **{"provider": provider}})

    if len(shows) == 0:
        return "No results found"

    show = max(shows, key=lambda show: fuzz.ratio(
        show["Title"].strip().casefold(), search.strip().casefold()))

    reply("Show: " + show["Title"] + " - " + show["Url"])
    if episode is None:
        reply("Description: " + show["Metadata"]["Description"][:454])
        return

    episodes = getJson("episodes", {"provider": show["provider"], "showurl": show["Url"]})
    if "error" in episodes:
        return episodes["message"]

    episodes = episodes["episodes"]
    if episode > len(episodes):
        return "Invalid episode number. Max episode is " + str(len(episodes))

    episode = episodes[episode]
    reply(episode["Title"] + " - " + episode["Url"])
    reply("Description: " + episode["Metadata"]["Description"][:454])
