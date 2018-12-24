import random
from pathlib import Path

from cloudbot import hook

yo_momma = do_it = puns = confucious_say = one_liner = wise_quotes = book_puns = lawyer_jokes = kero_sayings = ['']


def load_joke_file(path):
    """
    Loads all the lines from a file, excluding blanks and lines that have been 'commented out'.
    :type path: Path
    :rtype: List[str]
    """
    with path.open(encoding='utf-8') as f:
        return [line.strip() for line in f
                if line.strip()
                and not line.startswith('//')]


@hook.on_start()
def load_jokes(bot):
    """
    :type bot: cloudbot.bot.Cloudbot
    """
    global yo_momma, do_it, puns, confucious_say, one_liner, wise_quotes, book_puns, lawyer_jokes, kero_sayings

    data_directory = Path(bot.data_dir)

    yo_momma = load_joke_file(data_directory / 'yo_momma.txt')
    do_it = load_joke_file(data_directory / 'do_it.txt')
    puns = load_joke_file(data_directory / 'puns.txt')
    confucious_say = load_joke_file(data_directory / 'confucious.txt')
    one_liner = load_joke_file(data_directory / 'one_liners.txt')
    wise_quotes = load_joke_file(data_directory / 'wisdom.txt')
    book_puns = load_joke_file(data_directory / 'book_puns.txt')
    lawyer_jokes = load_joke_file(data_directory / 'lawyerjoke.txt')
    kero_sayings = load_joke_file(data_directory / 'kero.txt')


@hook.command()
def yomomma(text):
    """<nick> - Tells a yo momma joke to <nick>."""
    target = text.strip()
    return '{}, {}'.format(target, random.choice(yo_momma).lower())



@hook.command(autohelp=False)
def doit(message):
    """- Prints a do it line, example: mathematicians do with a pencil."""
    message(random.choice(do_it))


@hook.command(autohelp=False)
def pun(message):
    """- Come on everyone loves puns right?"""
    message(random.choice(puns))


@hook.command(autohelp=False)
def confucious(message):
    """- Confucious say man standing on toilet is high on pot.
    (Note that the spelling is deliberate: https://www.urbandictionary.com/define.php?term=Confucious)
    """
    message('Confucious say {}'.format(random.choice(confucious_say).lower()))


@hook.command(autohelp=False)
def dadjoke(message):
    """- Love em or hate em, bring on the dad jokes."""
    message(random.choice(one_liner))


@hook.command(autohelp=False)
def wisdom(message):
    """- Words of wisdom from various bathroom stalls."""
    message(random.choice(wise_quotes))


@hook.command(autohelp=False)
def bookpun(message):
    """- Suggests a pun of a book title/author."""
    # suggestions = ["Why not try", "You should read", "You gotta check out"]
    book = random.choice(book_puns)
    title = book.split(':')[0].strip()
    author = book.split(':')[1].strip()
    message("{} by {}".format(title, author))


@hook.command("boobs", "boobies")
def boobies(text):
    """<text> - Everything is better with boobies!"""
    boob = "\u2299"
    out = text.strip()
    out = out.replace('o', boob).replace('O', boob).replace('0', boob)
    if out == text.strip():
        return "Sorry I couldn't turn anything in '{}' into boobs for you.".format(out)
    return out


@hook.command("zombs", autohelp=False)
def zombs():
    """- Prints some fucked up shit."""
    out = "\u2299\u2299\u0505\u0F0D\u0020\u0E88\u0020\u25DE\u0C6A\u25DF\u0E88\u0020\u0F0D\u0648"
    return out


@hook.command("awesome", "iscool", "cool")
def awesome(text, is_nick_valid):
    """<nick> - Prints a link to show <nick> how awesome they are."""
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
    """- Peturns a triforce!"""
    top = ["\u00a0\u25b2", "\u00a0\u00a0\u25b2", "\u25b2", "\u00a0\u25b2"]
    bottom = ["\u25b2\u00a0\u25b2", "\u25b2 \u25b2", "\u25b2\u25b2"]
    message(random.choice(top))
    message(random.choice(bottom))


@hook.command("kero", "kerowhack")
def kero(text):
    """<text> - Returns the text input the way kerouac5 would say it."""
    keror = random.choice(kero_sayings).upper()
    if keror == "???? WTF IS":
        out = keror + " " + text.upper()
    else:
        out = text.upper() + " " + keror
    return out


@hook.command(autohelp=False)
def lawyerjoke(message):
    """- Returns a lawyer joke, so lawyers know how much we hate them."""
    message(random.choice(lawyer_jokes))


@hook.command("fuck", autohelp=False)
def fuck():
    """- Returns something funny."""
    return "something funny."
