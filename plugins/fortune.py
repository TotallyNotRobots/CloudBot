import random
from typing import List

from cloudbot import hook

fortunes: List[str] = []


@hook.on_start()
def load_fortunes(bot):
    path = bot.data_path / "fortunes.txt"
    fortunes.clear()
    with open(path, encoding="utf-8") as f:
        fortunes.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@hook.command(autohelp=False)
async def fortune():
    """- hands out a fortune cookie"""
    return random.choice(fortunes)
