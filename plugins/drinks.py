import json
import os
import random

from cloudbot import hook
from cloudbot.util import web

drink_data = []


@hook.onload()
def load_drinks(bot):
    """load the drink recipes"""
    drink_data.clear()
    with open(os.path.join(bot.data_dir, "drinks.json")) as json_data:
        drink_data.extend(json.load(json_data))


@hook.command('drink')
def drink_cmd(text, chan, action):
    """<nick> - makes the user a random cocktail."""
    index = random.randint(0, len(drink_data) - 1)
    drink = drink_data[index]['title']
    url = web.try_shorten(drink_data[index]['url'])
    if drink.endswith(' recipe'):
        drink = drink[:-7]
    contents = drink_data[index]['ingredients']
    out = "grabs some"
    for x in contents:
        if x == contents[len(contents) - 1]:
            out += " and {}".format(x)
        else:
            out += " {},".format(x)
    if drink[0].lower() in ['a', 'e', 'i', 'o', 'u']:
        article = 'an'
    else:
        article = 'a'
    out += "\x0F and makes {} {} \x02{}\x02. {}".format(text, article, drink, url)
    action(out, chan)
