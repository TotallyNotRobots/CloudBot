# Get various rss feeds
# Author: Matheus Fillipe
# Date: 13/10/2022


import feedparser
from bs4 import BeautifulSoup

from cloudbot import hook
from cloudbot.util.formatting import truncate

feeds = {
    ("hackernews", "hn"): "https://hnrss.org/newest",
    ("reddit", "r"): "https://www.reddit.com/r/all/.rss",
    ("slashdot", "sd"): "https://slashdot.org/index.rss",
    ("techmeme", "tm"): "https://www.techmeme.com/feed.xml",
    ("wired", "wi"): "https://www.wired.com/feed/rss",
}


def parsefeed(rss, n=1):
    """Get random news from fake news website."""
    feed = feedparser.parse(rss)
    article = feed["entries"][-n]
    body = BeautifulSoup(article["summary"], "html.parser").text
    return f"{article['title']} - {article['link']} - {truncate(body, 300)}"


def hookwrapper(cmds):
    rss = feeds[cmds]

    def rss_command(text, message):
        try:
            n = int(text)
        except ValueError:
            n = 1
        return parsefeed(rss, n)

    rss_command.__doc__ = f"""<number> - Get latest nth feed from {cmds[0]}"""
    return rss_command


for cmds in feeds:
    globals()[cmds[0]] = hook.command(*cmds, autohelp=False)(hookwrapper(cmds))
