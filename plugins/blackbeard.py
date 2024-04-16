import re

import requests
from thefuzz import fuzz

from cloudbot import hook

API = "https://blackbeard.fly.dev/"


def getJson(path, params={}):
    r = requests.get(API + path, params=params)
    return r.json()


def pastebin(text):
    url = "http://ix.io"
    payload = {"f:1=<-": text}
    response = requests.request("POST", url, data=payload)
    return response.text


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
    return (
        max(
            shows,
            key=lambda show: fuzz.ratio(
                show["Title"].strip().casefold(), search.strip().casefold()
            ),
        ),
        True,
    )


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

    show = max(
        shows,
        key=lambda show: fuzz.ratio(
            show["Title"].strip().casefold(), search.strip().casefold()
        ),
    )

    reply("Show/Movie: " + show["Title"] + " - " + show["Url"])
    if episode is None:
        msg = "Description: " + show["Metadata"]["Description"][:400].replace(
            "\n", " "
        )
        if len(show["Metadata"]["Description"]) > 512:
            msg += f' -->  {pastebin(show["Metadata"]["Description"])}'
        reply(msg)
        return

    episodes = getJson(
        "episodes", {"provider": show["provider"], "showurl": show["Url"]}
    )
    if "error" in episodes:
        return episodes["message"]

    episodes = episodes["episodes"]
    if episode > len(episodes):
        return "Invalid episode number. Max episode is " + str(len(episodes))

    episode = episodes[episode]
    url = episode["Url"]
    if len(url) > 150:
        url = pastebin(url)
    reply("Episode/Video: " + episode["Title"] + " - " + url)

    msg = "Description: " + episode["Metadata"]["Description"][:400].replace(
        "\n", " "
    )
    if len(episode["Metadata"]["Description"]) > 512:
        msg += f' -->  {pastebin(episode["Metadata"]["Description"])}'
    reply(msg)

    video = getJson(
        "video", {"provider": show["provider"], "epurl": episode["Url"]}
    )
    url = video.get("Request", {}).get("Url")
    cmd = video.get("Metadata", {}).get("CurlCommand")
    if cmd:
        cmd = f"{cmd} --compressed | mpv -"
        reply(f"Run with curl and mpv: {pastebin(cmd)}")
    if url:
        reply(f"Direct url: {pastebin(url)}")
