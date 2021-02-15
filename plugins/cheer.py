import random
import re
from typing import List

from cloudbot import hook
from cloudbot.bot import CloudBot

cheer_re = re.compile(r"\\o/", re.IGNORECASE)

cheers: List[str] = []


@hook.on_start()
def load_cheers(bot: CloudBot):
    cheers.clear()
    data_file = bot.data_path / "cheers.txt"
    with data_file.open(encoding="utf-8") as f:
        cheers.extend(line.strip() for line in f if not line.startswith("//"))


@hook.regex(cheer_re)
def cheer(chan, message):
    shit = random.choice(cheers)
    message(shit, chan)
