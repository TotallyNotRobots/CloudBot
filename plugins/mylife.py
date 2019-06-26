import functools
import random
import re

import requests

from cloudbot import hook
from cloudbot.util.http import parse_soup

fml_cache = []
mlia_cache = []


async def refresh_fml_cache(loop):
    """ gets a page of random FMLs and puts them into a dictionary """
    url = 'http://www.fmylife.com/random/'
    _func = functools.partial(requests.get, url, timeout=6)
    request = await loop.run_in_executor(None, _func)
    soup = parse_soup(request.text)

    for e in soup.find_all('p', {'class': 'block'}):
        # the /today bit is there to exclude fml news etc.
        a = e.find('a', {'href': re.compile('/article/today')})
        if not a:
            continue

        # the .html in the url must be removed before extracting the id
        fml_id = int(a['href'][:-5].split('_')[-1])
        text = a.text.strip()

        # exclude lengthy submissions and FML photos
        if len(text) > 375 or text[-3:].lower() != "fml":
            continue
        fml_cache.append((fml_id, text))


async def refresh_mlia_cache(loop):
    """ gets a page of random MLIAs and puts them into a dictionary """
    url = 'http://mylifeisaverage.com/{}'.format(random.randint(1, 11000))
    _func = functools.partial(requests.get, url, timeout=6)
    request = await loop.run_in_executor(None, _func)
    soup = parse_soup(request.text)

    for story in soup.find_all('div', {'class': 'story '}):
        mlia_id = story.find('span', {'class': 'left'}).a.text
        mlia_text = story.find('div', {'class': 'sc'}).text
        mlia_text = " ".join(mlia_text.split())
        mlia_cache.append((mlia_id, mlia_text))


@hook.on_start()
async def initial_refresh(loop):
    # do an initial refresh of the caches
    await refresh_fml_cache(loop)
    await refresh_mlia_cache(loop)


@hook.command(autohelp=False)
async def fml(reply, loop):
    """- gets a random quote from fmylife.com"""

    if fml_cache:
        # grab the last item in the fml cache and remove it
        fml_id, text = fml_cache.pop()
        # reply with the fml we grabbed
        reply('(#{}) {}'.format(fml_id, text))
    else:
        await refresh_fml_cache(loop)

    # refresh fml cache if its getting empty
    if len(fml_cache) < 3:
        await refresh_fml_cache(loop)


@hook.command(autohelp=False)
async def mlia(reply, loop):
    """- gets a random quote from MyLifeIsAverage.com"""

    if mlia_cache:
        # grab the last item in the mlia cache and remove it
        mlia_id, text = mlia_cache.pop()
        # reply with the mlia we grabbed
        reply('({}) {}'.format(mlia_id, text))
    else:
        await refresh_mlia_cache(loop)

    # refresh mlia cache if its getting empty
    if len(mlia_cache) < 3:
        await refresh_mlia_cache(loop)
