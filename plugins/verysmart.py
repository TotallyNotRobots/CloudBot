import codecs
import os
import random

from cloudbot import hook

vsquotes = []


@hook.on_start()
def load_quotes(bot):
    """- Import quotes from data directory."""
    vsquotes.clear()
    with codecs.open(
        os.path.join(bot.data_dir, "verysmart.txt"), encoding="utf-8"
    ) as fp:
        vsquotes.extend(quote.strip() for quote in fp.readlines())


@hook.command("smart", "verysmart", "vs", "iamverysmart", "iavs", autohelp=False)
def verysmart():
    """- Return a random choice from the quote list."""
    return random.choice(vsquotes)
