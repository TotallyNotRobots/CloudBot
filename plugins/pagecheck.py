import urllib.parse

import requests
import requests.exceptions

from cloudbot import hook
from cloudbot.util.http import parse_soup


@hook.command("down", "offline", "up")
def down(text):
    """<url> - checks if <url> is online or offline"""

    if "://" not in text:
        text = "https://" + text

    text = "https://" + urllib.parse.urlparse(text).netloc

    try:
        r = requests.get(text)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        return "{} seems to be down".format(text)
    else:
        return "{} seems to be up".format(text)


@hook.command()
def isup(text):
    """<url> - uses isup.me to check if <url> is online or offline"""
    url = text.strip()

    # slightly overcomplicated, esoteric URL parsing
    _, auth, path, _, _ = urllib.parse.urlsplit(url)

    domain = auth or path

    try:
        response = requests.get("https://isup.me/" + domain)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return "Failed to get status."
    if response.status_code != requests.codes.ok:
        return "Failed to get status."

    soup = parse_soup(response.text)

    content = soup.find("div", id="domain-main-content").text.strip()

    if "not just you" in content:
        return "It's not just you. {} looks \x02\x034down\x02\x0f from here!".format(
            url
        )

    if "is up" in content:
        return "It's just you. {} is \x02\x033up\x02\x0f.".format(url)

    return "Huh? That doesn't look like a site on the interweb."
