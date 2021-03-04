import feedparser

from cloudbot import hook
from cloudbot.util import web


@hook.command("meh", autohelp=False)
def meh():
    """- List the current meh.com deal."""
    url = "https://meh.com/deals.rss"

    feed = feedparser.parse(url)
    title = feed.entries[0].title
    link = web.try_shorten(feed.entries[0].link)

    return "meh.com: {} ({})".format(title, link)


@hook.command("slickdeals", autohelp=False)
def slickdeals():
    """- List the top 3 frontpage slickdeals.net deals."""
    url = "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1"

    feed = feedparser.parse(url)
    items = (
        "{} ({})".format(item.title, web.try_shorten(item.link))
        for item in feed.entries[:3]
    )

    out = "slickdeals.net: " + " \u2022 ".join(items)

    return out
