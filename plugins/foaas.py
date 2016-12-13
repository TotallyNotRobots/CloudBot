import requests
import random
from cloudbot import hook

FuckOffList = [    
        'donut',
        'bus',
        'chainsaw',
        'king',
        'madison',
        'gfy',
        'back',
        'keep',
        'name',
        'bday',
        'dalton',
        'ing',
        'nugget',
        'outside',
        'off',
        'problem',
        'shakespeare',
        'think',
        'thinking',
        'xmas',
        'yoda',
        'you'
                   ]

SingleFuckList = [
                    'bag',
                    'awesome',
                    'because',
                    'bucket',
                    'bye',
                    'cool',
                    'everyone',
                    'everything',
                    'flying',
                    'give',
                    'horse',
                    'life',
                    'looking',
                    'maybe',
                    'me',
                    'mornin',
                    'no',
                    'pink',
                    'retard',
                    'rtfm',
                    'sake',
                    'shit',
                    'single',
                    'thanks',
                    'that',
                    'this',
                    'too',
                    'tucker',
                    'zayn',
                    'zero'


                    ]

headers = {'Accept' : 'text/plain'}

@hook.command('fos','fuckoff','foaas')
def foaas(text, nick, message):
    '''fos [name] to tell some one to fuck off or just .fos for a generic fuckoff'''
    Fuckee = text.strip()
    Fucker = nick
    if Fuckee == '':
        r = requests.get('http://www.foaas.com/' + str(random.choice(SingleFuckList)) + Fucker,headers=headers)
        out = r.text
        message(out)
    else:
        r = requests.get('http://www.foaas.com/' + str(random.choice(FuckOffList)) + '/' + "\x02" + Fuckee + "\x02" + '/' + Fucker, headers=headers)
        out = r.text
        message(out)
