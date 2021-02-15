import random
from typing import List

from cloudbot import hook

topicchange_data: List[str] = []


@hook.on_start()
def load_topicchange(bot):
    topicchange_data.clear()
    with open((bot.data_path / "topicchange.txt"), encoding="utf-8") as f:
        topicchange_data.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@hook.command("changetopic", "discuss", "question", autohelp=False)
def topicchange(message):
    """- generates a random question to help start a conversation or change a topic"""
    message(random.choice(topicchange_data))
