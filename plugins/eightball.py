import codecs
import os
import random

from cloudbot import hook
from cloudbot.util import colors

responses = []


@hook.on_start()
def load_responses(bot):
    path = os.path.join(bot.data_dir, "8ball_responses.txt")
    responses.clear()
    with codecs.open(path, encoding="utf-8") as f:
        responses.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@hook.command("8ball", "8", "eightball")
async def eightball(action):
    """<question> - asks the all knowing magic electronic eight ball <question>"""
    magic = random.choice(responses)
    message = colors.parse("shakes the magic 8 ball... {}".format(magic))

    action(message)
