from cloudbot import hook
from cloudbot.util import web
import feedparser

@hook.command('meh', autohelp=False)
def meh():
	'''List the current meh.com deal.'''
	url = "https://meh.com/deals.rss"

	feed = feedparser.parse(url)
	title = feed.entries[0].title
	link = web.try_shorten(feed.entries[0].link)

	return "meh.com: {} ({})".format(title, link)

@hook.command('slickdeals', autohelp=False)
def slickdeals():
	'''List the top 3 frontpage slickdeals.net deals.'''
	url = "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1"

	feed = feedparser.parse(url)

	first = feed.entries[0].title, web.try_shorten(feed.entries[0].link)
	second = feed.entries[1].title, web.try_shorten(feed.entries[1].link)
	third = feed.entries[2].title, web.try_shorten(feed.entries[2].link)

	out = "slickdeals.net: "
	out += "{} ({}) • ".format(first[0], first[1])
	out += "{} ({}) • ".format(second[0], second[1])
	out += "{} ({})".format(third[0], third[1])

	return out
