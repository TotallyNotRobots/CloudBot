import random
import re

from cloudbot import hook

cheers = [
    "FUCK YEAH!",
    "HOORAH!",
    "HURRAY!",
    "OORAH!",
    "YAY!",
    "*\o/* CHEERS! *\o/*",
    "HOOHAH!",
    "HOOYAH!",
    "HUAH!",
    "♪  ┏(°.°)┛  ┗(°.°)┓ ♬",
]

cheer_re = re.compile(r'\\o/', re.IGNORECASE)


@hook.regex(cheer_re)
def cheer(chan, message):
    """
    :type chan: str
    """
    if chan not in ["#yogscast"]:
        shit = random.choice(cheers)
        message(shit, chan)
