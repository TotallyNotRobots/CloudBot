import json
import random
from typing import Dict, List

from cloudbot import hook

lenny_data: Dict[str, List[str]] = {}


@hook.on_start()
def load_faces(bot):
    lenny_data.clear()
    data_file = bot.data_path / "lenny.json"
    with data_file.open(encoding="utf-8") as f:
        lenny_data.update(json.load(f))


@hook.command(autohelp=False)
def lenny(message):
    """- why the shit not lennyface"""
    message(random.choice(lenny_data["lenny"]))


@hook.command(autohelp=False)
def flenny(message):
    """- flenny is watching."""
    message(random.choice(lenny_data["flenny"]))
