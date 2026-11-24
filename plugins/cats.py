from __future__ import annotations

from typing import TYPE_CHECKING

import requests
from requests import HTTPError

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.event_functions import EventReply


def get_data(url, reply: EventReply, bot, params=None):
    try:
        with requests.get(
            url, headers={"User-Agent": bot.user_agent}, params=params
        ) as r:
            r.raise_for_status()
    except HTTPError:
        reply("API error occurred.")
        raise

    return r


@hook.command(autohelp=False)
def cats(reply: EventReply, bot):
    """- gets a fucking fact about cats."""
    r = get_data(
        "https://catfact.ninja/fact", reply, bot, params={"max_length": 100}
    )
    json = r.json()
    return json["fact"]


@hook.command(autohelp=False)
def catgifs() -> str:  # pragma: no cover
    """- Cat gif API has been shut down."""
    return "Cat gif API has been shut down."
