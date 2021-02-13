import random

from cloudbot import hook

balls = ["(_)_)", "8", "B", "(___)__)", "(_)(_)", "(@)@)", "3"]
shaft = [
    "=",
    "==",
    "===",
    "====",
    "=====",
    "========",
    "/////////////////////////",
    "|||||||||||||",
    "\u2248\u2248\u2248",
]
head = ["D", "Q", ">", "|\u2283", "\u22d1", "\u22d9", "\u22d7"]
emission = ["~ ~ ~ ~", "~ * ~ &", "", "*~* *~* %"]
bodypart = [
    "face",
    "glasses",
    "thigh",
    "tummy",
    "back",
    "hiney",
    "hair",
    "boobs",
    "tongue",
]


@hook.command("penis", "bepis", autohelp=False)
def penis(text, message):
    """[nick] - much dongs, very ween, add a user nick as an arguement for slightly different 'output'"""
    if not text:
        message(
            "{}{}{}".format(
                random.choice(balls), random.choice(shaft), random.choice(head)
            )
        )
    else:
        person = text.split(" ")[0]
        message(
            "{}{}{}{} all over {}'s {}".format(
                random.choice(balls),
                random.choice(shaft),
                random.choice(head),
                random.choice(emission),
                person,
                random.choice(bodypart),
            )
        )
