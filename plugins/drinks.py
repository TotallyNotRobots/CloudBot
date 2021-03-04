import json
import random
from typing import Any, Dict, List

from cloudbot import hook
from cloudbot.bot import CloudBot
from cloudbot.util import formatting, web

drink_data: List[Dict[str, Any]] = []


@hook.onload()
def load_drinks(bot: CloudBot) -> None:
    """load the drink recipes"""
    drink_data.clear()
    with open(bot.data_path / "drinks.json", encoding="utf-8") as json_data:
        drink_data.extend(json.load(json_data))


@hook.command("drink")
def drink_cmd(text, chan, action):
    """<nick> - makes the user a random cocktail."""
    index = random.randint(0, len(drink_data) - 1)
    drink = drink_data[index]["title"]
    url = web.try_shorten(drink_data[index]["url"])
    if drink.endswith(" recipe"):
        drink = drink[:-7]

    contents = drink_data[index]["ingredients"]
    out = "grabs some "
    out += formatting.get_text_list(contents, "and")

    if drink[0].lower() in ["a", "e", "i", "o", "u"]:
        article = "an"
    else:
        article = "a"

    out += "\x0F and makes {} {} \x02{}\x02. {}".format(
        text, article, drink, url
    )
    action(out, chan)
