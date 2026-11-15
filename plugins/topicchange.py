from __future__ import annotations

import random
from typing import TYPE_CHECKING

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.event_functions import EventMessage

topicchange_data: list[str] = []


@hook.on_start()
def load_topicchange(bot) -> None:
    topicchange_data.clear()
    with open((bot.data_path / "topicchange.txt"), encoding="utf-8") as f:
        topicchange_data.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@hook.command("changetopic", "discuss", "question", autohelp=False)
def topicchange(message: EventMessage) -> None:
    """- generates a random question to help start a conversation or change a topic"""
    message(random.choice(topicchange_data))
