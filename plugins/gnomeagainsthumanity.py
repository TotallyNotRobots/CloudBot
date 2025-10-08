import json
import random
import re

from cloudbot import hook

gnomecards: dict[str, list[str]] = {}


@hook.on_start()
def shuffle_deck(bot):
    gnomecards.clear()
    with open((bot.data_path / "gnomecards.json"), encoding="utf-8") as f:
        gnomecards.update(json.load(f))


@hook.command("cah")
def CAHwhitecard(text):
    """<text> - Submit text to be used as a CAH whitecard"""
    return random.choice(gnomecards["black"]).format(text)


@hook.command("cahb")
def CAHblackcard(text):
    """<text> - Submit text with _ for the bot to fill in the rest. You can submit text with multiple _"""
    CardText = text.strip()

    def blankfiller(matchobj):
        return random.choice(gnomecards["white"])

    out = re.sub(r"\b_\b", blankfiller, CardText)
    return out
