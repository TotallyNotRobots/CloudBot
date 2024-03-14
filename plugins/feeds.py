import feedparser

from cloudbot import hook
from cloudbot.util import formatting, web


class FeedAlias:
    def __init__(self, url, limit=3):
        self.url = url
        self.limit = limit


ALIASES = {
    "xkcd": FeedAlias("https://xkcd.com/rss.xml"),
    "ars": FeedAlias("https://feeds.arstechnica.com/arstechnica/index"),
    "pip": FeedAlias("https://pypi.python.org/pypi?%3Aaction=rss", 6),
    "pypi": FeedAlias("https://pypi.python.org/pypi?%3Aaction=rss", 6),
    "py": FeedAlias("https://pypi.python.org/pypi?%3Aaction=rss", 6),
    "pipnew": FeedAlias(
        "https://pypi.python.org/pypi?%3Aaction=packages_rss", 5
    ),
    "pypinew": FeedAlias(
        "https://pypi.python.org/pypi?%3Aaction=packages_rss", 5
    ),
    "pynew": FeedAlias(
        "https://pypi.python.org/pypi?%3Aaction=packages_rss", 5
    ),
    "world": FeedAlias(
        "https://news.google.com/news?cf=all&ned=us&hl=en&topic=w&output=rss"
    ),
    "us": FeedAlias(
        "https://news.google.com/news?cf=all&ned=us&hl=en&topic=n&output=rss"
    ),
    "usa": FeedAlias(
        "https://news.google.com/news?cf=all&ned=us&hl=en&topic=n&output=rss"
    ),
    "nz": FeedAlias(
        "https://news.google.com/news?pz=1&cf=all&ned=nz&hl=en&topic=n&output=rss"
    ),
    "anand": FeedAlias("https://www.anandtech.com/rss/"),
    "anandtech": FeedAlias("https://www.anandtech.com/rss/"),
}


def format_item(item):
    url = web.try_shorten(item.link)
    title = formatting.strip_html(item.title)
    return "{} ({})".format(title, url)


@hook.command("feed", "rss", "news")
def rss(text):
    """<feed> - Gets the first three items from the RSS/ATOM feed <feed>."""
    t = text.lower().strip()
    if t in ALIASES:
        alias = ALIASES[t]
        addr = alias.url
        limit = alias.limit
    else:
        addr = text
        limit = 3

    feed = feedparser.parse(addr)
    if not feed.entries:
        return "Feed not found."

    out = []
    for item in feed.entries[:limit]:
        out.append(format_item(item))

    if "title" in feed.feed:
        start = "\x02{}\x02: ".format(feed.feed.title)
    else:
        start = ""

    return start + ", ".join(out)
