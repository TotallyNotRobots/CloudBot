import re
import urllib.parse

import requests
from requests import HTTPError

from cloudbot import hook
from cloudbot.util import formatting, web
from cloudbot.util.http import parse_xml

api_url = "https://api.wolframalpha.com/v2/query"
query_url = "https://www.wolframalpha.com/input/?i={}"


@hook.command("wolframalpha", "wa", "calc", "ca", "math", "convert")
def wolframalpha(text, bot, reply):
    """<query> - Computes <query> using Wolfram Alpha."""
    api_key = bot.config.get_api_key("wolframalpha")
    if not api_key:
        return "error: missing api key"

    params = {"input": text, "appid": api_key}
    request = requests.get(api_url, params=params)

    try:
        request.raise_for_status()
    except HTTPError as e:
        reply("Error getting query: {}".format(e.response.status_code))
        raise

    if request.status_code != requests.codes.ok:
        return "Error getting query: {}".format(request.status_code)

    result = parse_xml(request.content)

    # get the URL for a user to view this query in a browser
    short_url = web.try_shorten(query_url.format(urllib.parse.quote_plus(text)))

    pod_texts = []
    for pod in result.xpath("//pod[@primary='true']"):
        title = pod.attrib["title"]
        if pod.attrib["id"] == "Input":
            continue

        results = []
        for subpod in pod.xpath("subpod/plaintext/text()"):
            subpod = subpod.strip().replace("\\n", "; ")
            subpod = re.sub(r"\s+", " ", subpod)
            if subpod:
                results.append(subpod)
        if results:
            pod_texts.append(title + ": " + ", ".join(results))

    ret = " - ".join(pod_texts)

    if not pod_texts:
        return "No results."

    # I have no idea what this regex does.
    ret = re.sub(r"\\(.)", r"\1", ret)
    ret = formatting.truncate(ret, 250)

    if not ret:
        return "No results."

    return "{} - {}".format(ret, short_url)
