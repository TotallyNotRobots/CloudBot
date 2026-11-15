from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.event_functions import EventMessage

lenny_data: dict[str, list[str]] = {}


@hook.on_start()
def load_faces(bot) -> None:
    lenny_data.clear()
    data_file = bot.data_path / "lenny.json"
    with data_file.open(encoding="utf-8") as f:
        lenny_data.update(json.load(f))


@hook.command(autohelp=False)
def lenny(message: EventMessage) -> None:
    """- why the shit not lennyface"""
    message(random.choice(lenny_data["lenny"]))


@hook.command(autohelp=False)
def flenny(message: EventMessage) -> None:
    """- flenny is watching."""
    message(random.choice(lenny_data["flenny"]))
