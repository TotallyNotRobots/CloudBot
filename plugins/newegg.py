"""
newegg.py

Provides a command and URL parser for viewing newegg products.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""

import json
import re

import requests

from cloudbot import hook
from cloudbot.util import formatting, web

# CONSTANTS

ITEM_URL = "https://www.newegg.com/Product/Product.aspx?Item={}"

API_PRODUCT = "https://www.ows.newegg.com/Products.egg/{}"
API_SEARCH = "https://www.ows.newegg.com/Search.egg/Advanced"

NEWEGG_RE = re.compile(r"(?:(?:www.newegg.com|newegg.com)/Product/Product\.aspx\?Item=)([-_a-zA-Z0-9]+)", re.I)


# OTHER FUNCTIONS

def format_item(item, show_url=True):
    """ takes a newegg API item object and returns a description """
    title = formatting.truncate(item["Title"], 60)

    # format the rating nicely if it exists
    if not item["ReviewSummary"]["TotalReviews"] == "[]":
        rating = "Rated {}/5 ({} ratings)".format(item["ReviewSummary"]["Rating"],
                                                  item["ReviewSummary"]["TotalReviews"])
    else:
        rating = "No Ratings"

    if item["OriginalPrice"] and item["FinalPrice"] != item["OriginalPrice"]:
        price = "{FinalPrice}, was {OriginalPrice}".format(**item)
    else:
        price = item["FinalPrice"]

    tags = []

    if item["Instock"]:
        tags.append("\x02Stock Available\x02")
    else:
        tags.append("\x02Out Of Stock\x02")

    if item["IsFreeShipping"]:
        tags.append("\x02Free Shipping\x02")

    if item.get("IsPremierItem"):
        tags.append("\x02Premier\x02")

    if item["IsFeaturedItem"]:
        tags.append("\x02Featured\x02")

    # join all the tags together in a comma separated string ("tag1, tag2, tag3")
    tag_text = ", ".join(tags)

    if show_url:
        # create the item URL and shorten it
        url = web.try_shorten(ITEM_URL.format(item["NeweggItemNumber"]))
        return "\x02{}\x02 ({}) - {} - {} - {}".format(title, price, rating,
                                                       tag_text, url)
    else:
        return "\x02{}\x02 ({}) - {} - {}".format(title, price, rating,
                                                  tag_text)


# HOOK FUNCTIONS

@hook.regex(NEWEGG_RE)
def newegg_url(match):
    item_id = match.group(1)

    # newegg thinks it's so damn smart blocking my scraper
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) '
                      'Version/5.1 Mobile/9A334 Safari/7534.48.3',
        'Referer': 'http://www.newegg.com/'
    }

    request = requests.get(API_PRODUCT.format(item_id), headers=headers)
    request.raise_for_status()
    item = request.json()
    return format_item(item['Basic'], show_url=False)


# @hook.command()
def newegg(text, admin_log, reply):
    """<item name> - searches newegg.com for <item name>"""

    # form the search request
    request = {
        "Keyword": text,
        "Sort": "FEATURED"
    }

    # newegg thinks it's so damn smart blocking my scraper
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) '
                      'Version/5.1 Mobile/9A334 Safari/7534.48.3',
        'Referer': 'http://www.newegg.com/'
    }

    # submit the search request
    try:
        request = requests.post(
            'http://www.ows.newegg.com/Search.egg/Advanced',
            data=json.dumps(request).encode('utf-8'),
            headers=headers
        )
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        return "Unable to find product: {}".format(e)

    r = request.json()

    if not request.ok:
        if r.get("Message"):
            msg = "{ExceptionMessage}\n{ExceptionType}\n{StackTrace}".format(**r).replace("\r", "")
            url = web.paste(msg)
            admin_log("Newegg API Error: {ExceptionType}: {url}".format(url=url, **r))
            return "Newegg Error: {Message} (\x02{code}\x02)".format(code=request.status_code, **r)
        else:
            reply("Unknown error occurred.")
            request.raise_for_status()
            return

    # get the first result
    if r["ProductListItems"]:
        return format_item(r["ProductListItems"][0])
    else:
        return "No results found."
