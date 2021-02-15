import random

import requests

from cloudbot import hook
from cloudbot.bot import CloudBot
from cloudbot.util.http import parse_soup

search_url = "https://www.dogpile.com/search"

CERT_PATH = "dogpile.crt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 4.0.4; Galaxy Nexus Build/IMM76B) AppleWebKit/535.19 "
    "(KHTML, like Gecko) Chrome/18.0.1025.133 Mobile Safari/535.19"
}

session = requests.Session()


@hook.on_start()
def check_certs(bot: CloudBot):
    try:
        with requests.get(search_url):
            pass
    except requests.exceptions.SSLError:
        session.verify = str(bot.data_path / CERT_PATH)
    else:
        session.verify = None


def query(endpoint, text):
    params = {"q": " ".join(text.split())}
    with requests.get(
        search_url + "/" + endpoint,
        params=params,
        headers=HEADERS,
        verify=session.verify,
    ) as r:
        r.raise_for_status()
        return parse_soup(r.content)


@hook.command("dpis", "gis")
def dogpileimage(text):
    """<query> - Uses the dogpile search engine to search for images."""
    soup = query("images", text)
    results_container = soup.find("div", {"class": "images-bing__list"})
    if not results_container:
        return "No results found."

    results_list = results_container.find_all("div", {"class": "image"})
    if not results_list:
        return "No results found."

    image = random.choice(results_list)
    return image.find("a", {"class": "link"})["href"]


@hook.command("dp", "g", "dogpile")
def dogpile(text):
    """<query> - Uses the dogpile search engine to find shit on the web."""
    soup = query("web", text)
    results = soup.find_all("div", {"class": "web-bing__result"})
    if not results:
        return "No results found."

    result = results[0]
    result_url = result.find("a", {"class": "web-bing__title", "href": True})[
        "href"
    ]
    result_description = result.find(
        "span", {"class": "web-bing__description"}
    ).text
    return "{} -- \x02{}\x02".format(result_url, result_description)
