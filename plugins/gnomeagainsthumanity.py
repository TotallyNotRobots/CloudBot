import codecs
import json
import asyncio
import random
from cloudbot import hook
import re


@hook.on_start()
def shuffle_deck(bot):

    global gnomecards
    with codecs.open(os.path.join(bot.data_dir, "gnomecards.json"), encoding="utf-8") as f:
        gnomecards = json.load(f)


        
@hook.command('cah')
def CAHwhitecard(text, message):
    '''Submit text to be used as a CAH whitecard'''
    CardText = text.strip()
    message(random.choice(gnomecards['black']).format(text))


@hook.command('cahb')
def CAHblackcard(text, message):
    '''Submit text with _ for the bot to fill in the rest. You can submit text with multiple _'''
    CardText = text.strip()

    def blankfiller(matchobj):
        return random.choice(gnomecards['white'])

    out = re.sub(r'_', blankfiller, CardText)
    message(out)
