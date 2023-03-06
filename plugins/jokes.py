import random
from pathlib import Path
from typing import List

from cloudbot import hook

joke_lines = {}


def load_joke_file(path: Path) -> List[str]:
    """Loads all the lines from a file, excluding blanks and lines that have been 'commented out'."""
    with path.open(encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("//")
        ]


@hook.on_start()
def load_jokes(bot):
    """Load strings into memory from files in the data directory.
    Put 'NAME.txt' in `file_list` to make those strings available as `joke_lines['NAME']`.
    """
    file_list = [
        "yo_momma.txt",
        "do_it.txt",
        "puns.txt",
        "confucious.txt",
        "one_liners.txt",
        "wisdom.txt",
        "book_puns.txt",
        "lawyerjoke.txt",
        "kero.txt",
    ]
    for file_name in file_list:
        file_path = bot.data_path / file_name
        joke_lines[file_path.stem] = load_joke_file(file_path)


@hook.command()
def yomomma(text, nick, conn, is_nick_valid):
    """<nick> - Tells a yo momma joke to <nick>."""
    target = text.strip()
    if not is_nick_valid(target) or target.lower() == conn.nick.lower():
        target = nick
    joke = random.choice(joke_lines["yo_momma"]).lower()
    return "{}, {}".format(target, joke)


@hook.command(autohelp=False)
def doit(message):
    """- Prints a do it line, example: mathematicians do with a pencil."""
    message(random.choice(joke_lines["do_it"]))


@hook.command(autohelp=False)
def pun(message):
    """- Come on everyone loves puns right?"""
    message(random.choice(joke_lines["puns"]))


@hook.command(autohelp=False)
def confucious(message):
    """- Confucious say man standing on toilet is high on pot.
    (Note that the spelling is deliberate: https://www.urbandictionary.com/define.php?term=Confucious)
    """
    saying = random.choice(joke_lines["confucious"]).lower()
    message("Confucious say {}".format(saying))


@hook.command(autohelp=False)
def dadjoke(message):
    """- Love em or hate em, bring on the dad jokes."""
    message(random.choice(joke_lines["one_liners"]))


@hook.command(autohelp=False)
def wisdom(message):
    """- Words of wisdom from various bathroom stalls."""
    message(random.choice(joke_lines["wisdom"]))


@hook.command(autohelp=False)
def bookpun(message):
    """- Suggests a pun of a book title/author."""
    # suggestions = ["Why not try", "You should read", "You gotta check out"]
    message(random.choice(joke_lines["book_puns"]))


@hook.command("boobs", "boobies")
def boobies(text):
    """<text> - Everything is better with boobies!"""
    boob = "\u2299"
    out = text.strip()
    out = out.replace("o", boob).replace("O", boob).replace("0", boob)
    if out == text.strip():
        return (
            "Sorry I couldn't turn anything in '{}' into boobs for you.".format(
                out
            )
        )
    return out


@hook.command(autohelp=False)
def zombs():
    """- Prints some fucked up shit."""
    out = "\u2299\u2299\u0505\u0F0D\u0020\u0E88\u0020\u25DE\u0C6A\u25DF\u0E88\u0020\u0F0D\u0648"
    return out


@hook.command("awesome", "iscool", "cool")
def awesome(text, is_nick_valid):
    """<nick> - Returns a link to show <nick> how awesome they are.
    See https://github.com/sebastianbarfurth/is-awesome.cool
    """
    target = text.split(" ")[0]
    if not is_nick_valid(target):
        return "Sorry I can't tell {} how awesome they are.".format(target)
    link = "https://{}.is-awesome.cool/".format(target)
    return "{}: I am blown away by your recent awesome action(s). Please read \x02{}\x02".format(
        target, link
    )


@hook.command(autohelp=False)
def triforce(message):
    """- Returns a triforce!"""
    top = ["\u00a0\u25b2", "\u00a0\u00a0\u25b2", "\u25b2", "\u00a0\u25b2"]
    bottom = ["\u25b2\u00a0\u25b2", "\u25b2 \u25b2", "\u25b2\u25b2"]
    message(random.choice(top))
    message(random.choice(bottom))


@hook.command("kero", "kerowhack")
def kero(text):
    """<text> - Returns the text input the way kerouac5 would say it."""
    keror = random.choice(joke_lines["kero"]).upper()
    if keror == "???? WTF IS":
        out = keror + " " + text.upper()
    else:
        out = text.upper() + " " + keror
    return out


@hook.command(autohelp=False)
def lawyerjoke(message):
    """- Returns a lawyer joke, so lawyers know how much we hate them."""
    message(random.choice(joke_lines["lawyerjoke"]))


@hook.command(autohelp=False)
def fuck():
    """- Returns something funny."""
    return "something funny."
