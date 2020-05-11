import functools
import re

import requests

from cloudbot import hook
from cloudbot.util.http import parse_soup

fml_cache = []


@hook.on_start()
async def refresh_fml_cache(loop):
    """ gets a page of random FMLs and puts them into a dictionary """
    url = "http://www.fmylife.com/random/"
    _func = functools.partial(requests.get, url, timeout=6)
    request = await loop.run_in_executor(None, _func)
    soup = parse_soup(request.text)

    # the /today bit is there to exclude fml news etc.
    articles = soup.find_all(
        "a", {"class": "article-link", "href": re.compile("/article/today")}
    )
    for a in articles:
        # the .html in the url must be removed before extracting the id
        fml_id = int(a["href"][:-5].split("_")[-1])
        text = a.text.strip()

        # exclude lengthy submissions and FML photos
        if len(text) > 375 or text[-3:].lower() != "fml":
            continue
        fml_cache.append((fml_id, text))


@hook.command(autohelp=False)
async def fml(reply, loop):
    """- gets a random quote from fmylife.com"""

    if not fml_cache:
        await refresh_fml_cache(loop)

    # grab the last item in the fml cache and remove it
    fml_id, text = fml_cache.pop()
    # reply with the fml we grabbed
    reply("(#{}) {}".format(fml_id, text))

    # refresh fml cache if its getting empty
    if len(fml_cache) < 3:
        await refresh_fml_cache(loop)
