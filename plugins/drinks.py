from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING, Any

from cloudbot import hook
from cloudbot.util import formatting, web

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot
    from cloudbot.event_functions import EventAction

drink_data: list[dict[str, Any]] = []


@hook.on_start()
def load_drinks(bot: CloudBot) -> None:
    """load the drink recipes"""
    drink_data.clear()
    with open(bot.data_path / "drinks.json", encoding="utf-8") as json_data:
        drink_data.extend(json.load(json_data))


@hook.command("drink")
def drink_cmd(text, chan, action: EventAction) -> None:
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

    out += f"\x0f and makes {text} {article} \x02{drink}\x02. {url}"
    action(out, chan)
