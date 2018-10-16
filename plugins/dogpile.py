import random
import re
from urllib import parse

import requests
from bs4 import BeautifulSoup

from cloudbot import hook

search_url = "http://dogpile.com/search"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 4.0.4; Galaxy Nexus Build/IMM76B) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.133 Mobile Safari/535.19'
}


@hook.command("dpis", "gis")
def dogpileimage(text):
    """<query> - Uses the dogpile search engine to search for images."""
    image_url = search_url + "/images"
    params = {'q': " ".join(text.split())}
    r = requests.get(image_url, params=params, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.content)
    data = soup.find_all("script")[6].string
    link_re = re.compile('"url":"(.*?)",')
    linklist = link_re.findall(data)
    if not linklist:
        return "No results returned."

    image = parse.unquote(parse.unquote(random.choice(linklist)).split('ru=')[1].split('&')[0])
    return image


@hook.command("dp", "g", "dogpile")
def dogpile(text):
    """<query> - Uses the dogpile search engine to find shit on the web."""
    web_url = search_url + "/web"
    params = {'q': " ".join(text.split())}
    r = requests.get(web_url, params=params, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.content)
    results = soup.find('div', id="webResults")
    if not results:
        return "No results found."

    result_url = parse.unquote(
        parse.unquote(results.find_all('a', {'class': 'resultDisplayUrl'})[0]['href']).split(
            'ru=')[1].split('&')[0])
    result_description = results.find_all('div', {'class': 'resultDescription'})[0].text
    return "{} -- \x02{}\x02".format(result_url, result_description)
