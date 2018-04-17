import codecs
import os
import random

from cloudbot import hook

joke_data = {}

data_files = (
    "yo_momma",
    "do_it",
    "puns",
    "confucious",
    "one_liners",
    "wisdom",
    "book_puns",
    "lawyerjoke",
    "kero",
)


def _load_data(bot, name, file):
    with codecs.open(os.path.join(bot.data_dir, file), encoding="utf-8") as f:
        joke_data[name] = [
            line.strip() for line in f.readlines() if not line.startswith("//")
        ]


@hook.on_start()
def load_jokes(bot):
    """
    :type bot: cloudbot.bot.Cloudbot
    """

    for name in data_files:
        _load_data(bot, name, name + '.txt')


@hook.command()
def yomomma(text):
    """<nick> - tells a yo momma joke to <nick>"""
    target = text.strip()
    return '{}, {}'.format(target, random.choice(joke_data['yo_momma']).lower())


@hook.command(autohelp=False)
def doit(message):
    """- prints a do it line, example: mathmaticians do with a pencil"""
    message(random.choice(joke_data['do_it']))


@hook.command(autohelp=False)
def pun(message):
    """- Come on everyone loves puns right?"""
    message(random.choice(joke_data['puns']))


@hook.command(autohelp=False)
def confucious(message):
    """- confucious say man standing on toilet is high on pot."""
    message('Confucious say {}'.format(random.choice(joke_data['confucious']).lower()))


@hook.command(autohelp=False)
def dadjoke(message):
    """- love em or hate em, bring on the dad jokes."""
    message(random.choice(joke_data['one_liners']))


@hook.command(autohelp=False)
def wisdom(message):
    """- words of wisdom from various bathroom stalls."""
    message(random.choice(joke_data['wisdom']))


@hook.command(autohelp=False)
def bookpun(message):
    """- Suggests a pun of a book title/author."""
    book = random.choice(joke_data['book_puns']).split(':')
    title = book[0].strip()
    author = book[1].strip()
    message("{} by {}".format(title, author))


@hook.command("boobs", "boobies")
def boobies(text):
    """- prints boobies!"""
    boob = "\u2299"
    out = text.strip()
    out = out.replace('o', boob).replace('O', boob).replace('0', boob)
    if out == text.strip():
        return "Sorry I couldn't turn anything in '{}' into boobs for you.".format(out)

    return out


@hook.command("awesome", "iscool", "cool")
def awesome(text, is_nick_valid):
    """- Prints a webpage to show <nick> how awesome they are."""
    link = 'http://is-awesome.cool/{}'
    nick = text.split(' ')[0]
    if is_nick_valid(nick):
        return "{}: I am blown away by your recent awesome action(s). Please read \x02{}\x02".format(
            nick, link.format(nick)
        )
    else:
        return "Sorry I can't tell {} how awesome they are.".format(nick)


@hook.command(autohelp=False)
def triforce(message):
    """- returns a triforce!"""
    top = ["\u00a0\u25b2", "\u00a0\u00a0\u25b2", "\u25b2", "\u00a0\u25b2"]
    bottom = ["\u25b2\u00a0\u25b2", "\u25b2 \u25b2", "\u25b2\u25b2"]
    message(random.choice(top))
    message(random.choice(bottom))


@hook.command("kero", "kerowhack")
def kero(text):
    """- Returns the text input the way kerouac5 would say it."""
    keror = random.choice(joke_data['kero']).upper()
    if keror == "???? WTF IS":
        out = keror + " " + text.upper()
    else:
        out = text.upper() + " " + keror
    return out


@hook.command(autohelp=False)
def lawyerjoke(message):
    """- returns a lawyer joke, so lawyers know how much we hate them"""
    message(random.choice(joke_data['lawyerjoke']))
