import json
import urllib.parse

import requests

from cloudbot import hook

API = "https://api.datamuse.com/words?"
MAX_DISPLAY_WORDS = 20


def get(**params):
    r = requests.get(
        API
        + "&".join(
            [
                f"{key}={urllib.parse.quote(value)}"
                for key, value in params.items()
            ]
        )
    )
    if r.status_code != 200:
        return None, r.status_code
    return json.loads(r.content), r.status_code


def words(**params):
    r, code = get(**params)
    if r is None:
        return "Request failed. Status code: " + code
    return ", ".join([w["word"] for w in r[:MAX_DISPLAY_WORDS]])


def targs(text):
    return text.strip().split()


@hook.command()
def rhyme(text, bot, nick):
    """<word> - get rhymes for the word."""
    args = targs(text)
    if not args:
        return "This command requires one argument"
    return words(rel_rhy=args[0])


@hook.command()
def adj(text, bot, nick):
    """<word> - get adjectives that are often used to describe input word."""
    args = targs(text)
    return words(rel_jjb=args[0])


@hook.command()
def noun(text, bot, nick):
    """<noun> - nouns that are often described by the adjective <noun>."""
    args = targs(text)
    if not args:
        return "This command requires one argument"
    return words(rel_jja=args[0])


@hook.command()
def soundlike(text, bot, nick):
    """<word> - words that sound like <word>."""
    args = targs(text)
    return words(sl=args[0])


@hook.command()
def mean(text, bot, nick):
    """<text> - words with a meaning similar to <text>."""
    return words(ml=text)


@hook.command()
def rhymerel(text, bot, nick):
    """<word1> <word2> - words that rhyme with <word1> that are related to <word2>."""
    args = targs(text)
    return words(ml=args[0], rel_rhy=args[0])


@hook.command()
def adjrel(text, bot, nick):
    """<word1> <word2> - adjectives describing word1 sorted by how related they are to word2."""
    args = targs(text)
    return words(rel_jjb=args[0], topics=args[1])
