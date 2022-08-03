# Various wikis searching, random page and next results thanks to https://github.com/barrust/mediawiki
# Author: Matheus Fillipe
# Date: 31/07/2022


import mwparserfromhell
from mediawiki import MediaWiki, exceptions

from cloudbot import hook
from cloudbot.util import formatting

# List of wikis and their API's
# The key is a tuple starting with the wiki name all those values will be used as the bot commands.
# The value is the api url.
# (commands, tuple, ...): "api_url"
APIS = {
    ("wikipedia", "w"): "https://en.wikipedia.org/w/api.php",
    ("uncyclopedia", "uw"): "https://uncyclopedia.com/w/api.php",
    ("tcrf", "wt"): "https://tcrf.net/api.php",
    ("wikitionary", "wd"): "https://wiktionary.org/w/api.php",
}

results = {}

MAX_SUMMARY = 250


@hook.on_start()
def on_start():
    global results, API
    results = {}
    for wiki in APIS:
        results[wiki] = []
        APIS[wiki] = MediaWiki(APIS[wiki])


def summary_from_page(text: str) -> str:
    """Tries to parse a summary out from the wiki markdown."""
    summary = ""
    for line in text.split("\n"):
        line = line.strip()
        if not (line.endswith("]]") or line.endswith("}}")) and len(line) > 100:
            summary += line
        if len(summary) > MAX_SUMMARY:
            break
    wikicode = mwparserfromhell.parse(summary)
    return wikicode.strip_code()


def wikipop(wiki: tuple) -> str:
    """Pops the first result from the list and returns the formated summary."""
    global results
    wikipedia = APIS[wiki]
    if len(results[wiki]) == 0:
        return "No [more] results found."
    i = 0
    while i < len(results[wiki]):
        try:
            title = results[wiki].pop(0)
            page = wikipedia.page(title)
            break
        except exceptions.DisambiguationError:
            i += 1
    else:
        return "No results found."

    # If the api doesn't have the TextExtract extension installed, we need to parse it
    desc = page.summary or summary_from_page(page.wikitext)
    url = page.url

    desc = formatting.truncate(desc, MAX_SUMMARY)
    return "\x02{}\x02 :: {} :: {}".format(title, desc, url)


def search(wiki: tuple, query: str) -> str:
    """Searches for the query and returns the formated summary populating the
    results list."""
    global results
    wikipedia = APIS[wiki]
    results[wiki] = wikipedia.search(query)
    return wikipop(wiki)


def process_irc_input(wiki: tuple, text: str) -> str:
    """Processes the input from the irc user and returns a random result from
    the wiki if no arguments is passed, otherwise performs the search."""
    global results
    if text.strip() == "":
        wikipedia = APIS[wiki]
        results[wiki] = [wikipedia.random()]
        return wikipop(wiki)
    return search(wiki, text)


def make_search_hook(commands):
    name = commands[0]

    def wikisearch(text, bot):
        return process_irc_input(commands, text)
    wikisearch.__doc__ = f"<query> - Searches the {name} for <query>. If you don't pass any query, it will return a random result."
    return wikisearch


def make_next_hook(commands):
    name = commands[0]

    def wikinext(text, bot):
        return wikipop(commands)

    wikinext.__doc__ = f" - Gets the next result from the last {name} search"
    return wikinext


# Store as a dict to avoide repetition and so that the cloudbot hook.command call atually works
hooks_map = {}
for commands in APIS:
    hooks_map[tuple(commands)] = make_search_hook(commands)

    # creates the next commands
    next_cmds = ()
    for command in commands:
        if len(command) > 2:
            command += "_next"
        else:
            command += "n"
        next_cmds += (command,)

    hooks_map[next_cmds] = make_next_hook(commands)

for cmds in hooks_map:
    # HACK to make the cloudbot hook.command call work
    locals()[cmds[0]] = hooks_map[cmds]
    eval(f"hook.command(*cmds, autohelp=False)({cmds[0]})")
