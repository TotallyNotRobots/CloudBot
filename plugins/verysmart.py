import random
from typing import List

from cloudbot import hook

vsquotes: List[str] = []


@hook.on_start()
def load_quotes(bot):
    """- Import quotes from data directory."""
    vsquotes.clear()
    with open((bot.data_path / "verysmart.txt"), encoding="utf-8") as fp:
        vsquotes.extend(quote.strip() for quote in fp.readlines())


@hook.command(
    "smart", "verysmart", "vs", "iamverysmart", "iavs", autohelp=False
)
def verysmart():
    """- Return a random choice from the quote list."""
    return random.choice(vsquotes)
