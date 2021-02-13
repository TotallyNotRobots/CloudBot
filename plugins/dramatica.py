import re
from urllib import parse

import requests
from lxml import html
from requests import HTTPError

from cloudbot import hook
from cloudbot.util import formatting

api_url = "http://encyclopediadramatica.se/api.php"
ed_url = "http://encyclopediadramatica.se/"


@hook.command()
def drama(text, reply):
    """<phrase> - gets the first paragraph of the Encyclopedia Dramatica article on <phrase>"""

    search_response = requests.get(
        api_url, params={"action": "opensearch", "search": text}
    )

    try:
        search_response.raise_for_status()
    except HTTPError:
        reply("Error searching: {}".format(search_response.status_code))
        raise

    if search_response.status_code != requests.codes.ok:
        return "Error searching: {}".format(search_response.status_code)

    data = search_response.json()

    if not data[1]:
        return "No results found."
    article_name = data[1][0].replace(" ", "_")

    url = ed_url + parse.quote(article_name, "")

    page_response = requests.get(url)

    try:
        page_response.raise_for_status()
    except HTTPError:
        reply("Error getting page: {}".format(page_response.status_code))
        raise

    if page_response.status_code != requests.codes.ok:
        return "Error getting page: {}".format(page_response.status_code)

    page = html.fromstring(page_response.text)

    for p in page.xpath('//div[@id="bodyContent"]/p'):
        if p.text_content():
            summary = " ".join(p.text_content().splitlines())
            summary = re.sub(r"\[\d+\]", "", summary)
            summary = formatting.truncate(summary, 220)
            return "{} - {}".format(summary, url)

    return "Unknown Error."
