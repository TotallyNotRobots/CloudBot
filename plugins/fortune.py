import asyncio
import codecs
import os
import random

from cloudbot import hook


@hook.on_start()
def load_fortunes(bot):
    path = os.path.join(bot.data_dir, "fortunes.txt")
    global fortunes
    with codecs.open(path, encoding="utf-8") as f:
        fortunes = [line.strip() for line in f.readlines() if not line.startswith("//")]


@hook.command(autohelp=False)
@asyncio.coroutine
def fortune():
    """- hands out a fortune cookie"""
    return random.choice(fortunes)
