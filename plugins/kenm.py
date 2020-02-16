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
    kenm_data.clear()
    with codecs.open(os.path.join(bot.data_dir, "kenm.txt"), encoding="utf-8") as f:
        kenm_data.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@hook.command("kenm", autohelp=False)
def kenm(message):
    """- Wisdom from Ken M."""
    message(random.choice(kenm_data))
