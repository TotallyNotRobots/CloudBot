"""
Etymology plugin

Authors:
    - GhettoWizard
    - Scaevolus
    - linuxdaemon <linuxdaemon@snoonet.org>
"""
import re

import requests
from bs4 import BeautifulSoup
from requests import HTTPError

from cloudbot import hook


@hook.command("e", "etymology")
def etymology(text, reply):
    """<word> - retrieves the etymology of <word>
    :type text: str
    :type reply: types.FunctionType
    """

    url = 'http://www.etymonline.com/index.php'

    response = requests.get(url, params={"term": text})

    try:
        response.raise_for_status()
    except HTTPError as e:
        reply("Error reaching etymonline.com: {}".format(e.response.status_code))
        raise

    if response.status_code != requests.codes.ok:
        return "Error reaching etymonline.com: {}".format(response.status_code)

    soup = BeautifulSoup(response.text, "lxml")

    block = soup.find('div', class_=re.compile("word--.+"))

    if not block:
        return 'No etymology found for {} :('.format(text)

    etym = ' '.join(e.text for e in block.div)

    etym = ' '.join(etym.splitlines())

    etym = ' '.join(etym.split())

    if len(etym) > 400:
        etym = etym[:etym.rfind(' ', 0, 400)] + ' ...'

    return etym
