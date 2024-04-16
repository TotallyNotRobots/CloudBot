# Get news from https://newsapi.org
# Author: Matheus Fillipe
# Date: 11/08/2020

import re
from dataclasses import dataclass
from random import choice

import feedparser
from bs4 import BeautifulSoup
from newsapi import NewsApiClient, const

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util.formatting import truncate
from cloudbot.util.queue import Queue

fakenews_feeds = [
    "http://www.theonion.com/feeds/rss",
    "http://newsthump.com/feed/",
    "https://www.thepoke.co.uk/category/news/feed/",
    "http://babylonbee.com/feed",
    "http://www.theblaze.com/feed/",
]


@dataclass
class Article:
    source: str
    author: str
    title: str
    description: str
    url: str
    urlToImage: str
    publishedAt: str
    content: str

    @staticmethod
    def from_json(json):
        return Article(
            json["source"].get("name", ""),
            json.get("author", ""),
            json.get("title", ""),
            json.get("description", ""),
            json.get("url", ""),
            json.get("urlToImage", ""),
            json.get("publishedAt", ""),
            json.get("content", "") or "",
        )

    def __post_init__(self, link: str = None):
        self.header = f"\x02{self.source}\x02: {self.publishedAt} {self.title} - {self.url} - "
        self.body = truncate(self.content, 500)

    def __str__(self):
        return self.header


results_queue = Queue()


def pop_many(results, reply):
    for _ in range(1):
        try:
            r = results.pop()
            reply(str(r))
            if r.body:
                reply(r.body)
        except IndexError:
            return "No [more] results found."


@hook.command("newsn", autohelp=False)
def newsn(text, chan, nick, reply):
    """<nick> - Returns next search result for news command for nick or yours by default"""
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

    return pop_many(results, reply)


@hook.command("news", autohelp=False)
def news(text, chan, nick, reply):
    """<category> <query> - Get news from newsapi.org"""
    api = bot.config.get_api_key("newsapi")
    if not api:
        return "This command requires a newsapi.org API key."
    newsapi = NewsApiClient(api_key=api)

    # If (country) in text
    co = re.match(r"\(([a-z]{2})\)", text)
    if co:
        co = co.group(1)
        if co not in const.countries:
            return f"Invalid country. Valid countries: {', '.join(const.countries)}"
        text = text.replace(f"({co})", "").strip()

    cat = text.split(" ")[0]
    if cat not in const.categories:
        for c in const.categories:
            if c.startswith(cat):
                cat = c
                break
        else:
            return f"Invalid category: {cat}. Valid categories: {', '.join(const.categories)}"

    query = text.replace(cat, "").strip() or None

    top_headlines = newsapi.get_top_headlines(q=query, category=cat, country=co)

    results_queue[chan][nick] = [
        Article.from_json(json) for json in top_headlines["articles"]
    ]
    return pop_many(results_queue[chan][nick], reply)


@hook.command("fakenews", autohelp=False)
def fakenews(text, chan, nick, reply):
    """Get random news from fake news website."""
    rss = choice(fakenews_feeds)
    feed = feedparser.parse(rss)
    article = choice(feed["entries"])
    body = BeautifulSoup(article["summary"], "html.parser").text
    return f"{article['title']} - {article['link']} - {truncate(body, 300)}"
