from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot
    from cloudbot.event_functions import EventMessage

cheer_re = re.compile(r"\\o/", re.IGNORECASE)

cheers: list[str] = []


@hook.on_start()
def load_cheers(bot: CloudBot) -> None:
    cheers.clear()
    data_file = bot.data_path / "cheers.txt"
    with data_file.open(encoding="utf-8") as f:
        cheers.extend(line.strip() for line in f if not line.startswith("//"))


@hook.regex(cheer_re)
def cheer(chan, message: EventMessage) -> None:
    shit = random.choice(cheers)
    message(shit, chan)
