import codecs
import json
import os
import random
import re

from cloudbot import hook


@hook.on_start()
def shuffle_deck(bot):
    global gnomecards
    with codecs.open(os.path.join(bot.data_dir, "gnomecards.json"), encoding="utf-8") as f:
        gnomecards = json.load(f)


@hook.command('cah')
def CAHwhitecard(text):
    """<text> - Submit text to be used as a CAH whitecard"""
    return random.choice(gnomecards['black']).format(text)


@hook.command('cahb')
def CAHblackcard(text):
    """<text> - Submit text with _ for the bot to fill in the rest. You can submit text with multiple _"""
    CardText = text.strip()

    # noinspection PyUnusedLocal
    def blankfiller(matchobj):
        return random.choice(gnomecards['white'])

    out = re.sub(r'\b_\b', blankfiller, CardText)
    return out
