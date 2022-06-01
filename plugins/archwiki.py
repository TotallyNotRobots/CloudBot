from cloudbot import hook
from gazpacho import get, Soup
import logging
import urllib.parse

API = "https://wiki.archlinux.org/index.php?profile=default&fulltext=Search&search="

logger = logging.getLogger("cloudbot")

pages = []

def next():
    global pages
    try:
        page = pages.pop(0)
    except IndexError:
        return "No more pages."
    temp = page.find("div", {"class": "mw-search-result-heading"})
    title = temp.text
    description = page.find(
        "div", {"class": "mw-search-result-data"}, mode="first"
    ).text
    link = f"https://wiki.archlinux.org{temp.find('a').attrs['href']}"

    return f"{title} - {description} - {link}"

@hook.command()
def awn(text):
    return next()

@hook.command()
def aw(text, bot, nick):
    """<query> - Find archwiki pages about."""

    global pages

    try:
        page = get(API + urllib.parse.quote(text))
    except Exception as e:
        logger.error(e)
        return "Could not get data from archwiki."

    html = Soup(page)
    pages = html.find("li", {"class": "mw-search-result"}, mode="all")
    return next()
