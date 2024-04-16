# Various wikis searching, random page and next results thanks to https://github.com/barrust/mediawiki
# Author: Matheus Fillipe
# Date: 31/07/2022


import mwparserfromhell
from mediawiki import MediaWiki, exceptions

from cloudbot import hook
from cloudbot.util import formatting
from cloudbot.util.queue import Queue

# List of wikis and their API's
# The key is a tuple starting with the wiki name all those values will be used as the bot commands.
# The value is the api url.
# (commands, tuple, ...): "api_url"
APIS = {
    ("wikipedia", "w"): "https://en.wikipedia.org/w/api.php",
    ("wikinews", "wnews"): "https://en.wikinews.org/w/api.php",
    ("uncyclopedia", "uw"): "https://uncyclopedia.com/w/api.php",
    ("desclicopedia", "desc"): "https://desciclopedia.org/api.php",
    ("tcrf", "wt"): "https://tcrf.net/api.php",
    ("wikitionary", "wd"): "https://wiktionary.org/w/api.php",
    ("esolangs", "wel"): "https://esolangs.org/w/api.php",
    ("archwiki", "warch"): "https://wiki.archlinux.org/api.php",
    ("gentoo", "wgentoo"): "https://wiki.gentoo.org/api.php",
    ("animanga", "fa"): "https://animanga.fandom.com/api.php",
    ("monica", "fmnc"): "https://monica.fandom.com/pt-br/api.php",
    ("fandomlinux", "flinux"): "https://linux.fandom.com/api.php",
    ("starwars", "fsw"): "https://starwars.fandom.com/api.php",
    ("microsoft", "fms"): "https://microsoft.fandom.com/api.php",
    ("apple", "fapple"): "https://apple.fandom.com/api.php",
    ("fandomminecraft", "fmc"): "https://minecraft.fandom.com/api.php",
    ("fandompokemon", "fpkm"): "https://pokemon.fandom.com/api.php",
    ("digimon", "fdgm"): "https://digimon.fandom.com/api.php",
    ("roblox", "froblox"): "https://roblox.fandom.com/api.php",
    ("nintendo", "fnintendo"): "https://nintendo.fandom.com/api.php",
    ("malware", "wmal"): "https://malwiki.org/api.php",
}

results = {}

MAX_SUMMARY = 250


@hook.on_start()
def on_start():
    global results, API
    results = {}
    for wiki in APIS:
        try:
            results[wiki] = Queue()
            results[wiki].metadata.wiki = MediaWiki(APIS[wiki])
        except Exception:
            print(f"Failed to connect to {APIS[wiki]}")
            continue


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


def wikipop(wiki: tuple, chan, nick, user=None) -> str:
    """Pops the first result from the list and returns the formated summary."""
    global results
    if user:
        queue = results[wiki][chan][user]
    else:
        queue = results[wiki][chan][nick]
    wikipedia = results[wiki].metadata.wiki
    if len(queue) == 0:
        return "No [more] results found."
    i = 0
    while i < len(queue):
        try:
            title = queue.pop()
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
    return f"\x02{title}\x02 :: {desc} :: {url}"


def search(wiki: tuple, query: str, chan, nick) -> str:
    """Searches for the query and returns the formated summary populating the
    results list."""
    global results
    wikipedia = results[wiki].metadata.wiki
    results[wiki][chan][nick] = wikipedia.search(query)
    return wikipop(wiki, chan, nick)


def process_irc_input(wiki: tuple, text: str, chan, nick) -> str:
    """Processes the input from the irc user and returns a random result from
    the wiki if no arguments is passed, otherwise performs the search."""
    global results
    if text.strip() == "":
        wikipedia = results[wiki].metadata.wiki
        results[wiki][chan][nick] = [wikipedia.random()]
        return wikipop(wiki, chan, nick)
    return search(wiki, text, chan, nick)


def make_search_hook(commands):
    name = commands[0]

    def wikisearch(text, bot, chan, nick):
        return process_irc_input(commands, text, chan, nick)

    wikisearch.__doc__ = f"<query> - Searches the {name} for <query>. If you don't pass any query, it will return a random result. Use .wikilist to know more wiki commands."
    return wikisearch


def make_next_hook(commands):
    name = commands[0]

    def wikinext(text, bot, chan, nick):
        global results
        user = text.strip().split()[0] if text.strip() else None
        if user:
            if user not in results[commands][chan]:
                return f"Nick '{user}' has no queue."
        else:
            user = None
        return wikipop(commands, chan, nick, user)

    wikinext.__doc__ = f" - Gets the next result from the last {name} search"
    return wikinext


@hook.command("wikilist", autohelp=False)
def wikilist(text, bot, chan, nick):
    """List all wikisi and their commands"""
    return "Available wikis: " + " - ".join([": ".join(w) for w in APIS.keys()])


# Store as a dict to avoid repetition and so that the cloudbot hook.command call atually works
hooks_map = {}
for commands in APIS:
    hooks_map[tuple(commands)] = make_search_hook(commands)

    # creates the next commands
    next_cmds = ()
    for command in commands:
        if len(command) > 4:
            command += "_next"
        else:
            command += "n"
        next_cmds += (command,)

    hooks_map[next_cmds] = make_next_hook(commands)

for cmds in hooks_map:
    globals()[cmds[0]] = hook.command(*cmds, autohelp=False)(hooks_map[cmds])
