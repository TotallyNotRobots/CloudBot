import random

from cloudbot import hook
from cloudbot.util import http

types = ["trivia", "math", "date", "year"]


@hook.command(autohelp=False)
def fact(reply):
    """- Gets a random fact about numbers or dates."""
    fact_type = random.choice(types)
    try:
        json = http.get_json(
            "https://numbersapi.com/random/{}?json".format(fact_type)
        )
    except Exception:
        reply("There was an error contacting the numbersapi.com API.")
        raise

    response = json["text"]
    return response
