# https://howlongtobeat.com - How Long To Beat games
# Author: Matheus Fillipe
# Date: 29/09/2022

from dataclasses import dataclass

import requests

from cloudbot import hook
from cloudbot.util.queue import Queue


@dataclass
class Game:
    name: str
    url: str
    main_story: int
    main_extras: int
    completionist: int

    def __str__(self):
        return f"{self.name} - {self.url} - Main Story: {self.main_story/3600:.2f} hours - Main + Extras: {self.main_extras/3600:.2f} hours - Completionist: {self.completionist/3600:.2f} hours"


results_queue = Queue()


URL = "https://howlongtobeat.com/api/search"
GAME_URL = "https://howlongtobeat.com/game/{}"

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0",
    "Referer": "https://howlongtobeat.com/?q=the%2520last%2520of%2520us",
}

json_data = {
    "searchType": "games",
    "searchTerms": [
        "the",
        "last",
        "of",
        "us",
    ],
    "searchPage": 1,
    "size": 20,
    "searchOptions": {
        "games": {
            "userId": 0,
            "platform": "",
            "sortCategory": "popular",
            "rangeCategory": "main",
            "rangeTime": {
                "min": 0,
                "max": 0,
            },
            "gameplay": {
                "perspective": "",
                "flow": "",
                "genre": "",
            },
            "modifier": "",
        },
        "users": {
            "sortCategory": "postcount",
        },
        "filter": "",
        "sort": 0,
        "randomizer": 0,
    },
}


@hook.command("hltbn", autohelp=False)
def hltbn(text, nick, chan):
    """Displays next game in queue for nick."""
    global results_queue

    if text:
        nick = text.strip().split()[0]
        if nick not in results_queue[chan]:
            return f"{nick} has no hltb game in queue."

    if len(results_queue[chan][nick]) == 0:
        return "No [more] results for you"

    game: Game = results_queue[chan][nick].pop()
    return str(game)


@hook.command("howlongtobeat", "hltb", autohelp=False)
def howlongtobeat(text, nick, chan):
    """<game> - Search for a game on How Long To Beat"""
    global results_queue
    json_data["searchTerms"] = text.split()
    response = requests.post(URL, headers=headers, json=json_data)
    if not response.ok:
        return f"Error: {response.status_code}"
    results_queue[chan][nick] = [
        Game(
            data["game_name"],
            GAME_URL.format(data["game_id"]),
            int(data["comp_main"]),
            int(data["comp_all"]),
            int(data["comp_100"]),
        )
        for data in response.json()["data"]
    ]
    return hltbn("", nick, chan)
