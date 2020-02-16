import codecs
import os
import random

from cloudbot import hook

fortunes = []


@hook.on_start()
def load_fortunes(bot):
    path = os.path.join(bot.data_dir, "fortunes.txt")
    fortunes.clear()
    with codecs.open(path, encoding="utf-8") as f:
        fortunes.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@hook.command(autohelp=False)
async def fortune():
    """- hands out a fortune cookie"""
    return random.choice(fortunes)
