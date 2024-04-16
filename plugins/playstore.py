# Author: Matheus Fillipe
# Date: 07/11/2022
# Description: Search on playstore

from typing import Optional

from bs4 import BeautifulSoup
from google_play_scraper import app, search
from pydantic import BaseModel, Field, validator

from cloudbot import hook
from cloudbot.util import formatting
from cloudbot.util.queue import Queue


class App(BaseModel):
    appId: str
    title: str
    score: Optional[float]
    genre: str
    price: float
    currency: str
    description: str
    installs: str
    url: Optional[str] = Field(alias="_url")

    @validator("score", always=True)
    def set_score(cls, v, values, **kwargs):
        if v is not None:
            return round(v, 2)

    @validator("description", always=True)
    def set_description(cls, v, values, **kwargs):
        desc = v.replace("\n", " ").replace("\r", " ")
        # Remove HTML tags
        soup = BeautifulSoup(desc, "html.parser")
        return soup.get_text()

    @validator("url", always=True)
    def set_url(cls, v, values, **kwargs):
        """Set the eggs field based upon a spam value."""
        return app(values["appId"])["url"]

    def __str__(self):
        return f"{self.title} - {self.price}{self.currency} - \x02Score:\x02 {self.score} - \x02Genre:\x02 {self.genre} - \x02Downloads:\x02 {self.installs} - {formatting.truncate(self.description, 100)} - {self.url}"


results_queue = Queue()


def pop3(results, reply):
    for _ in range(3):
        try:
            reply(str(results.pop()))
        except IndexError:
            return "No [more] results found."


@hook.command("playstoren", "playn", autohelp=False)
def playn(text, bot, chan, nick, reply):
    """<nick> - Returns next search result for pkg command for nick or yours by default"""
    global results_queue
    results = results_queue[chan][nick]
    user = text.strip().split()[0] if text.strip() else ""
    if user:
        if user in results_queue[chan]:
            results = results_queue[chan][user]
        else:
            return f"Nick '{user}' has no queue."

    if len(results) == 0:
        return "No [more] results found."

    return pop3(results, reply)


@hook.command("playstore", "play", autohelp=False)
def playstore(text, bot, chan, nick, reply):
    """Searches on playstore."""
    global results_queue
    if not text:
        return "Please specify a search query"
    results = [App.parse_obj(s) for s in search(text)]
    results_queue[chan][nick] = results
    results = results_queue[chan][nick]
    if results is None or len(results) == 0:
        return "No [more] results found."

    return pop3(results, reply)
