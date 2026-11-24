from __future__ import annotations

import random
from typing import TYPE_CHECKING

from cloudbot import hook
from cloudbot.util import http

if TYPE_CHECKING:
    from cloudbot.event_functions import EventReply

types = ["trivia", "math", "date", "year"]


@hook.command(autohelp=False)
def fact(reply: EventReply):
    """- Gets a random fact about numbers or dates."""
    fact_type = random.choice(types)
    try:
        json = http.get_json(f"http://numbersapi.com/random/{fact_type}?json")
    except Exception:
        reply("There was an error contacting the numbersapi.com API.")
        raise

    return json["text"]
