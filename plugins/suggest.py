from __future__ import annotations

import json
from typing import TYPE_CHECKING

import requests

from cloudbot import hook
from cloudbot.util import formatting

if TYPE_CHECKING:
    from cloudbot.event_functions import EventReply


@hook.command()
def suggest(text, reply: EventReply):
    """<phrase> - Gets suggested phrases for a google search"""
    params = {"output": "json", "client": "hp", "q": text}

    try:
        request = requests.get(
            "http://google.com/complete/search", params=params
        )
        request.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        reply(f"Could not get suggestions: {e}")
        raise

    page = request.text

    page_json = page.split("(", 1)[1][:-1]

    suggestions = json.loads(page_json)[1]
    suggestions = [suggestion[0] for suggestion in suggestions]

    if not suggestions:
        return "No suggestions found."

    out = formatting.strip_html(", ".join(suggestions))

    return formatting.truncate(out, 200)
