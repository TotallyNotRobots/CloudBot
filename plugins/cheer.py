import random
import re
from pathlib import Path

from cloudbot import hook

cheer_re = re.compile(r'\\o/', re.IGNORECASE)

cheers = []


@hook.on_start
def load_cheers(bot):
    cheers.clear()
    data_file = Path(bot.data_dir) / "cheers.txt"
    with data_file.open(encoding='utf-8') as f:
        cheers.extend(line.strip() for line in f if not line.startswith('//'))


@hook.regex(cheer_re)
def cheer(chan, message):
    """
    :type chan: str
    """
    shit = random.choice(cheers)
    message(shit, chan)
