import codecs
import os
import random

from cloudbot import hook

fmklist = []


@hook.on_start()
def load_fmk(bot):
    """
    :type bot: cloudbot.bot.Cloudbot
    """
    fmklist.clear()
    with codecs.open(
        os.path.join(bot.data_dir, "fmk.txt"), encoding="utf-8"
    ) as f:
        fmklist.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@hook.command("fmk", autohelp=False)
def fmk(text, message):
    """[nick] - Fuck, Marry, Kill"""
    message(
        " {} FMK - {}, {}, {}".format(
            (text.strip() if text.strip() else ""),
            random.choice(fmklist),
            random.choice(fmklist),
            random.choice(fmklist),
        )
    )
