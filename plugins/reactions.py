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
    global reactionmacros
    with codecs.open(os.path.join(bot.data_dir, "reactionmacros.json"), encoding="utf-8") as macros:
        reactionmacros = json.load(macros)

        
@hook.command('dwi', 'dealwithit')
def deal_with_it(text, message):
    """Tell some one in the channel to deal with it. File located in reactions.py"""
    PersonNeedsToDeal = text.strip()
    message('{} {}'.format(random.choice(deal_with_it_phrases).format(PersonNeedsToDeal), random.choice(reactionmacros['DWImacros'])))


@hook.command('fp', 'facepalm')
def face_palm(text,message):
    """Expresses your frustration with another user. File located in reactions.py"""
    FacePalmer = text.strip()
    message('Dammit {} {}'.format(FacePalmer, random.choice(reactionmacros['Facepalmmacros'])))

    
@hook.command('hd', 'headdesk')
def head_desk(nick, message):
    """Hit your head against the desk becausae of a user. Code located in reactions.py"""
    idiot = nick.strip()
    message('{} {}'.format(idiot, random.choice(reactionmacros['HeadDeskMacros'])))

    
@hook.command('fetish', 'tmf')
def my_fetish(nick, message):
    """Did some one just mention what your fetish was? Let them know! Code located in reactions.py"""
    PersonToShareFetishWith = nick.strip()
    message('{} {}'.format(PersonToShareFetishWith, random.choice(reactionmacros['Fetishmacros'])))
