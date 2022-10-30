# Author: Matheus Fillipe
# Date: 29/10/2022
# Description: Simple APIs with Python that don't even require auth

import requests
from time import time
from cloudbot import hook

GETS = {
    ("uselessfact", "uf"): {"url": "https://uselessfacts.jsph.pl/random.json?language=en", "key": "text"},
    ("catfact", "cf"): {"url": "https://catfact.ninja/fact", "key": "fact"},
    ("dogfact", "df"): {"url": "https://dog-api.kinduff.com/api/facts", "key": "facts"},
    ("chucknorris", "cn"): {"url": "https://api.chucknorris.io/jokes/random", "key": "value"},
    ("insult", "i"): {"url": "https://evilinsult.com/generate_insult.php?lang=en&type=json", "key": "insult"},
    ("joke", "j"): {"url": "https://official-joke-api.appspot.com/random_joke", "key": "setup"},
    ("yomama", "ym"): {"url": "http://api.yomomma.info/", "key": "joke"},
    ("xkcd", "x"): {"url": "https://xkcd.com/info.0.json", "key": "img"},
    ("quote", "q"): {"url": "https://api.quotable.io/random", "key": "content"},
    ("cat", "c"): {"url": "https://api.thecatapi.com/v1/images/search", "key": "url"},
    ("dog", "d"): {"url": "https://dog.ceo/api/breeds/image/random", "key": "message"},
    ("bird", "b"): {"url": "https://some-random-api.ml/img/birb", "key": "link"},
    ("fox", "f"): {"url": "https://some-random-api.ml/img/fox", "key": "link"},
    ("koala", "k"): {"url": "https://some-random-api.ml/img/koala", "key": "link"},
    ("panda", "p"): {"url": "https://some-random-api.ml/img/panda", "key": "link"},
    ("redpanda", "rp"): {"url": "https://some-random-api.ml/img/red_panda", "key": "link"},
}


def get_json(key, url):
    r = requests.get(url)
    r = r.json()
    return r[key]

def make_hook(commands):
    name = commands[0]
    def _hook(text, bot, chan, nick):
        return get_json(**GETS[commands])

    _hook.__doc__ = f"- returns a {name}"
    return _hook

for cmds in GETS:
    globals()[cmds[0]] = hook.command(*cmds, autohelp=False)(make_hook(cmds))

@hook.command("pop", autohelp=False)
def pop(text, bot, chan, nick):
    """- returns a estimative of the current world population"""
    r = requests.get(f"https://www.census.gov/popclock/data/population.php/world?_={int(time())}")
    r = r.json()
    return f"World population: {r['world']['population']}"

@hook.command("fake", autohelp=False)
def fake(text, bot, chan, nick):
    """- returns a fake user"""
    r = requests.get("https://randomuser.me/api/")
    r = r.json()['results'][0]
    return f"name: {r['name']['first']} {r['name']['last']}, {r['email']}, phone: {r['phone']}, location: {r['location']['city']}, {r['location']['state']}, {r['location']['country']}"

@hook.command("commit", autohelp=False)
def commit(text, bot, chan, nick):
    """- returns a random commit message"""
    r = requests.get("http://whatthecommit.com/index.txt")
    return r.text
