import re
from collections import defaultdict
from typing import Dict

from cloudbot import hook
from cloudbot.util import http
from cloudbot.util.pager import CommandPager, paginated_list

search_pages: Dict[str, Dict[str, CommandPager]] = defaultdict(dict)


class Game:
    __slots__ = ("cmds", "name")

    def __init__(self, *cmds, name=None):
        self.cmds = cmds
        if name is None:
            name = cmds[0]

        self.name = name


GAMES = (
    Game("nfl"),
    Game("mlb"),
    Game("nba"),
    Game("ncb", "ncaab"),
    Game("ncf", "ncaaf"),
    Game("nhl"),
    Game("wnba"),
)


@hook.command("morescore", autohelp=False)
def morescore(text, chan, conn):
    """[pagenum] - if a score list has lots of results the results are pagintated. If the most recent search is
    paginated the pages are stored for retreival. If no argument is given the next page will be returned else a page
    number can be specified."""
    chan_cf = chan.casefold()
    pages = search_pages[conn.name].get(chan_cf)
    if not pages:
        return "There are no score pages to show."

    return pages.handle_lookup(text)


def page_scores(conn, chan, scores):
    pager = paginated_list(scores, delim=" | ", pager_cls=CommandPager)
    search_pages[conn.name][chan.casefold()] = pager
    page = pager.next()
    if len(pager) > 1:
        page[-1] += " .morescore"

    return page


def scrape_scores(conn, chan, game, text):
    if not text:
        text = " "

    response = http.get_html(
        "http://scores.espn.go.com/{}/bottomline/scores".format(game),
        decode=False,
    )
    score = response.text_content()
    raw = score.replace("%20", " ")
    raw = raw.replace("^", "")
    raw = raw.replace("&", "\n")
    pattern = re.compile(r"{}_s_left\d+=(.*)".format(game))
    scores = []
    for match in re.findall(pattern, raw):
        if text.lower() in match.lower():
            scores.append(match)

    return page_scores(conn, chan, scores)


def score_hook(game):
    def func(conn, chan, text):
        return scrape_scores(conn, chan, game.name, text)

    func.__name__ = "{}_scores".format(game.name)
    func.__doc__ = (
        "[team city] - gets the score or next scheduled game for the specified team. "
        "If no team is specified all games will be included."
    )
    return func


def init_hooks():
    for game in GAMES:
        func = score_hook(game)
        globals()[func.__name__] = hook.command(*game.cmds, autohelp=False)(
            func
        )


init_hooks()
