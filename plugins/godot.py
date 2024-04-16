"""Maybe more godot relatd stuff in the future."""

import datetime
import urllib.parse

import pyocr.builders
import requests
from gazpacho import Soup, get
from PIL import Image

from cloudbot import hook


@hook.command(autohelp=False)
def jamdate(reply):
    """- Next godot jam date"""
    try:
        url_soup = Soup(get("https://godotwildjam.com"))
        url = url_soup.find("a", {"class": "elementor-button-link"})[0].attrs[
            "href"
        ]
        soup = Soup(get(url))
        elm = soup.find("div", {"class": "date_data"})
        text = elm.text
        from_date = elm.find("span")[0].text
        to_date = elm.find("span")[1].text
        reply(f"itch.io Godot Wild Jam: {text} {from_date} to {to_date}")
        from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S")
        to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S")
    except Exception:
        now = datetime.datetime.utcnow()
        firstday = now.replace(day=1)
        # This is the friday after the 1st weekend
        friday = 12 - firstday.weekday()
        from_date = firstday.replace(day=friday, hour=20, minute=0)
        to_date = from_date + datetime.timedelta(days=7)

    start_time_left = from_date - datetime.datetime.utcnow()
    end_time_left = to_date - datetime.datetime.utcnow()

    if end_time_left.days < 0:
        reply("This month's Godot Wild Jam is over.")
        now = datetime.datetime.utcnow()
        firstday = now.replace(day=1, month=now.month + 1)
        # This is the friday after the 1st weekend
        friday = 12 - firstday.weekday()
        from_date = firstday.replace(day=friday, hour=20, minute=0)
        to_date = from_date + datetime.timedelta(days=7)

        start_time_left = from_date - datetime.datetime.utcnow()
        end_time_left = to_date - datetime.datetime.utcnow()

    if start_time_left.days < 0:
        reply("Jam has already begun.")
    else:
        reply(
            f"Next Jam starts in {start_time_left.days} days {start_time_left.seconds//3600} hours {(start_time_left.seconds//60)%60} minutes."
        )
    reply(
        f"Jam ends in {end_time_left.days} days {end_time_left.seconds//3600} hours {(end_time_left.seconds//60)%60} minutes."
    )


@hook.command()
def godocs(text, reply):
    """<text> - Searches on godot documentation"""
    # url encode
    query = urllib.parse.quote(text)
    url = f"https://docs.godotengine.org/_/api/v2/search/?q={query}&project=godot&version=stable&language=en"
    data = get(url)

    i = 0
    used = set()
    for item in data["results"]:
        if i == 4:
            break
        description = ""
        for block in item["blocks"]:
            if block["type"] == "section":
                if block["content"]:
                    limit = 128
                    description += block["content"][:limit]
                    if len(description) > limit:
                        description += "..."
                break

        if item["path"] in used:
            continue

        i += 1
        used.add(item["path"])
        reply(
            f"{item['title']}: {description} - {item['domain'] + item['path']}"
        )


def capitalize(word: str) -> str:
    return word[0].upper() + word[1:]


class WildJamCardPaser:
    def __init__(self, theme_url, cards_url):
        self.tool = pyocr.tesseract
        self.theme_url = theme_url
        self.cards_url = cards_url

    def orc_image(self, img):
        txt = self.tool.image_to_string(
            img, lang="eng", builder=pyocr.builders.TextBuilder()
        )
        return txt.strip().lower().replace("\n", " ")

    def get_cards(self):
        img = Image.open(requests.get(self.cards_url, stream=True).raw)

        # Split img horizontally into 3 parts
        width, height = img.size
        img1 = img.crop((0, 0, width / 3, height))
        img2 = img.crop((width / 3, 0, width * 2 / 3, height))
        img3 = img.crop((width * 2 / 3, 0, width, height))
        return [
            capitalize(self.orc_image(img1)),
            capitalize(self.orc_image(img2)),
            capitalize(self.orc_image(img3)),
        ]

    def get_theme(self):
        img = Image.open(requests.get(self.theme_url, stream=True).raw)
        return capitalize(self.orc_image(img).split()[-1])


@hook.command("theme", autohelp=False)
def theme(reply):
    """- Current godot wild jam theme"""
    soup = Soup(get("https://godotwildjam.com"))
    elm = soup.find("div", {"class": "page-content"})
    title = elm.find(
        "h1", {"class": "elementor-heading-title elementor-size-default"}
    )[0].text

    not_started = "theme to be announced" in title.lower()
    if not_started:
        reply(title)
        return

    elms = soup.find("div", {"class": "elementor-widget-image"}, mode="all")
    theme_url = elms[1].find("img").attrs["src"]
    cards_url = elms[2].find("img").attrs["src"]
    parser = WildJamCardPaser(theme_url, cards_url)
    theme = parser.get_theme()
    cards = parser.get_cards()

    reply(
        f"\x02{title}\x02: {theme} - \x02CARDS: \x02{cards[0]}, {cards[1]}, {cards[2]}"
    )
