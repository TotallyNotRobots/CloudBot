"""Searches wikipedia and returns first sentence of article
Scaevolus 2009"""

import json
import re
import requests

from cloudbot import hook
from cloudbot.util import formatting

api_url = "http://en.wikipedia.org/w/api.php"

paren_re = re.compile(r'\s*\(.*\)$')


@hook.command("wiki", "wikipedia", "w")
def wiki(text, reply):
    """<phrase> - Gets first sentence of Wikipedia article on <phrase>."""

    text = text.strip()

    # both 'info' and 'extracts' are needed to fetch the URL
    search_params = {
        'format': 'json',
        'action': 'query',
        'generator': 'search',
        'prop': 'info|extracts',
        'inprop': 'url',
        'exintro': 1,
        'explaintext': 1,
        'gsrsearch': text
    }

    # Fetch data from the Wikipedia API
    try:
        request = requests.get(api_url, params=search_params)
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        reply("Could not get Wikipedia page: {}".format(e))
        raise
    response = json.loads(request.text)

    if 'query' not in response:
        return 'No results found.'

    # Take most relevant result
    for p in response['query']['pages'].items():
        if p[1]['index'] == 1:
            page = p[1]

    # Format the URL for output
    url = requests.utils.quote(page['fullurl'], ':/%')

    # Format the description for output
    desc = formatting.truncate(page['extract'], (370 - len(url)))

    return '{} {}'.format(desc, url)
