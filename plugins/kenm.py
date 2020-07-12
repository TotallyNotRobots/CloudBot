import codecs
import os
import random

from cloudbot import hook

kenm_data = []


@hook.on_start()
def load_kenm(bot):
    """
    :type bot: cloudbot.bot.Cloudbot
    """
    with codecs.open(
        os.path.join(bot.data_dir, "kenm.txt"), encoding="utf-8"
    ) as f:
        new_data = [
            line.strip() for line in f.readlines() if not line.startswith("//")
        ]

    kenm_data.clear()
    kenm_data.extend(new_data)


@hook.command("kenm", autohelp=False)
def kenm(message):
    """- Wisdom from Ken M."""
    message(random.choice(kenm_data))
