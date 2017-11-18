import codecs
import json
import asyncio
import os

import random
from cloudbot import hook


deal_with_it_phrases = [ 'Stop complaining, \x02{}\x02, and',
               'Jesus fuck \x02{}\x02, just',
               'Looks like \x02{}\x02 needs to',
               'Ever think that \x02{}\x02 just needs to']


@hook.on_start()
def load_macros(bot):
    global reaction_macros
    with codecs.open(os.path.join(bot.data_dir, "reaction_macros.json"), encoding="utf-8") as macros:
        reaction_macros = json.load(macros)

        
@hook.command('dwi', 'dealwithit')
def deal_with_it(text, message):
    """Tell <nick> in the channel to deal with it. Code located in reactions.py"""
    person_needs_to_deal = text.strip()
    message('{} {}'.format(random.choice(deal_with_it_phrases).format(person_needs_to_deal), random.choice(reaction_macros['DWImacros'])))


@hook.command('fp', 'facepalm')
def face_palm(text, message):
    """Expresses your frustration with <Nick>. Code located in reactions.py"""
    face_palmer = text.strip()
    message('Dammit {} {}'.format(FacePalmer, random.choice(reaction_macros['Facepalmmacros'])))

    
@hook.command('hd', 'headdesk')
def head_desk(text, message):
    """Hit your head against the desk becausae of <nick>. Code located in reactions.py"""
    idiot = text.strip()
    message('{} {}'.format(idiot, random.choice(reaction_macros['HeadDeskMacros'])))

    
@hook.command('fetish', 'tmf')
def my_fetish(text, message):
    """Did some one just mention what your fetish was? Let <nick> know! Code located in reactions.py"""
    person_to_share_fetish_with = text.strip()
    message('{} {}'.format(person_to_share_fetish_with, random.choice(reaction_macros['Fetishmacros'])))
