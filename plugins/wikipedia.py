"""Searches wikipedia and returns first sentence of article
Scaevolus 2009"""

import re

import requests

from cloudbot import hook
from cloudbot.util import formatting
from cloudbot.util.http import parse_xml

api_prefix = "http://en.wikipedia.org/w/api.php"
search_url = api_prefix + "?action=opensearch&format=xml"
description_fetch_url = api_prefix + "?action=query&format=xml&prop=extracts&explaintext=true&exintro=true&exsectionformat=plain"
random_url = api_prefix + "?action=query&format=xml&list=random&rnlimit=1&rnnamespace=0"

paren_re = re.compile(r'\s*\(.*\)$')


@hook.command("wiki", "wikipedia", "w")
def wiki(text, reply):
    """<phrase> - Gets first sentence of Wikipedia article on <phrase>."""

    try:
        request = requests.get(search_url, params={'search': text.strip()})
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        reply("Could not get Wikipedia page: {}".format(e))
        raise

    x = parse_xml(request.text)

    ns = '{http://opensearch.org/searchsuggest2}'
    items = x.findall(ns + 'Section/' + ns + 'Item')

    if not items:
        if x.find('error') is not None:
            return 'Could not get Wikipedia page: %(code)s: %(info)s' % x.find('error').attrib

        return 'No results found.'

    def extract(item):
        return [item.find(ns + i).text for i in
                ('Text', 'Url')]

    title, url = extract(items[0])

    def get_description(request_title):
        try:
            maximum_desc_len = 200
            desc_request_params = {'exchars': maximum_desc_len,
                                   'titles': request_title}
            description_request = requests.get(description_fetch_url, params=desc_request_params)
            description_request.raise_for_status()
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            reply("Could not get Wikipedia page description: {}".format(e))
            raise

        y = parse_xml(description_request.text)
        try:
            plain_desc = y.find('query').find('pages').find('page').find('extract').text
        except AttributeError as e:
            reply("Could not extract the description of the article: {}".format(e))
            raise

        return plain_desc

    desc = get_description(title)

    if 'may refer to' in desc:
        title, url = extract(items[1])
        desc = get_description(title)

    title = paren_re.sub('', title)

    if title.lower() not in desc.lower():
        desc = title + desc

    desc = ' '.join(desc.split())  # remove excess spaces
    desc = formatting.truncate(desc, 200)

    return '{} :: {}'.format(desc, requests.utils.quote(url, ':/%'))
