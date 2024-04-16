import logging
import urllib.parse

from gazpacho import Soup, get

from cloudbot import hook

API_ARCH = "https://wiki.archlinux.org/index.php?profile=default&fulltext=Search&search="
API_GENTOO = (
    "https://wiki.gentoo.org/index.php?profile=default&fulltext=Search&search="
)
MAX_TEXT_LENGTH = 250

logger = logging.getLogger("cloudbot")

pages = {
    API_GENTOO: [],
    API_ARCH: [],
}


def get_short(link):
    print(link)
    soup = Soup(get(link))
    text = ""
    for p in soup.find("div", {"class": "mw-parser-output"}).find(
        "p", mode="all"
    ):
        add = p.strip().strip()
        text += (" " if add.endswith(".") else ". ") + add
        if len(text) > MAX_TEXT_LENGTH:
            break
    if len(text) >= MAX_TEXT_LENGTH - 3:
        text = text[: MAX_TEXT_LENGTH - 3] + "..."
    return text


def next(api):
    global pages
    try:
        page = pages[api].pop(0)
    except IndexError:
        return "No more pages."
    temp = page.find("div", {"class": "mw-search-result-heading"})
    title = temp.text
    description = page.find(
        "div", {"class": "mw-search-result-data"}, mode="first"
    ).text
    link = f"https://{urllib.parse.urlparse(api).netloc}{temp.find('a').attrs['href']}"
    short = get_short(link)[:MAX_TEXT_LENGTH]

    return f"{title} :: {description} :: {short} :: {link}"


@hook.command()
def awn(text):
    return next(API_ARCH)


@hook.command()
def aw(text, bot, nick):
    """<query> - Find archwiki pages about."""
    global pages

    try:
        page = get(API_ARCH + urllib.parse.quote(text))
    except Exception as e:
        logger.error(e)
        return "Could not get data from archwiki."

    html = Soup(page)
    pages[API_ARCH] = html.find("li", {"class": "mw-search-result"}, mode="all")
    return next(API_ARCH)


@hook.command()
def gwn(text):
    return next(API_GENTOO)


@hook.command()
def gw(text, bot, nick):
    """<query> - Find gentoo pages about."""
    global pages

    try:
        page = get(API_GENTOO + urllib.parse.quote(text))
    except Exception as e:
        logger.error(e)
        return "Could not get data from gentoowiki"

    html = Soup(page)
    pages[API_GENTOO] = html.find(
        "li", {"class": "mw-search-result"}, mode="all"
    )
    return next(API_GENTOO)
