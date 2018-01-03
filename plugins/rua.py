import requests
from bs4 import BeautifulSoup

from cloudbot import hook


@hook.command('ruad', 'rud', 'ruadick')
def RUADICK(text, message):
    """<username> - checks ruadick.com to see if you're a dick on reddit"""
    DickCheck = text.strip()
    dickstatus = requests.get('http://www.ruadick.com/user/{}'.format(DickCheck))
    dickstatus.raise_for_status()
    DickSoup = BeautifulSoup(dickstatus.content, 'lxml')
    Dickstr = str(DickSoup.h2)

    dickstrip = Dickstr.lstrip('<h2>').rstrip('</h2>')

    if dickstrip == 'None':
        message('I can\'t find that user')
    else:
        message('{} {}'.format(dickstrip, dickstatus.url))
