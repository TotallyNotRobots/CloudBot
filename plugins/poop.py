# Funny prank

from random import choice

from cloudbot import hook

SENTENCES = [
    "Leaves a dump on {}'s head",
    "Poops hard over {}'s foot",
    "Sharts on {}'s face",
    "Defecates out of control all around {}",
    "Farts and poops while {} smells it",
    "Feeds {} by pooping on his mouth,",
]


@hook.command("poop", autohelp=False)
def poop(text):
    """<nick> -- Makes the bot poop"""
    if not text.strip():
        return "💩"
    return choice(SENTENCES).format(text.strip())
