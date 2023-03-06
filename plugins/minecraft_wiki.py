import re
from urllib.parse import quote

import requests
from lxml import html

from cloudbot import hook
from cloudbot.util import formatting

api_url = "https://minecraft.gamepedia.com/api.php?action=opensearch"
mc_url = "https://minecraft.gamepedia.com/"


@hook.command()
def mcwiki(text, reply):
    """<phrase> - gets the first paragraph of the Minecraft Wiki article on <phrase>"""

    try:
        request = requests.get(api_url, params={"search": text.strip()})
        request.raise_for_status()
        j = request.json()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        reply("Error fetching search results: {}".format(e))
        raise
    except ValueError as e:
        reply("Error reading search results: {}".format(e))
        raise

    if not j[1]:
        return "No results found."

    # we remove items with a '/' in the name, because
    # gamepedia uses sub-pages for different languages
    # for some stupid reason
    items = [item for item in j[1] if "/" not in item]

    if items:
        article_name = items[0].replace(" ", "_").encode("utf8")
    else:
        # there are no items without /, just return a / one
        article_name = j[1][0].replace(" ", "_").encode("utf8")

    url = mc_url + quote(article_name, "")

    try:
        request_ = requests.get(url)
        request_.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        reply("Error fetching wiki page: {}".format(e))
        raise

    page = html.fromstring(request_.text)

    for p in page.xpath('//div[@class="mw-content-ltr"]/p'):
        if p.text_content():
            summary = " ".join(p.text_content().splitlines())
            summary = re.sub(r"\[\d+\]", "", summary)
            summary = formatting.truncate(summary, 200)
            return "{} :: {}".format(summary, url)

    # this shouldn't happen
    return "Unknown Error."
