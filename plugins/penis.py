from __future__ import annotations

import random
from typing import TYPE_CHECKING

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.event_functions import EventMessage

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
def penis(text, message: EventMessage) -> None:
    """[nick] - much dongs, very ween, add a user nick as an argument for slightly different 'output'"""
    if not text:
        message(
            f"{random.choice(balls)}{random.choice(shaft)}{random.choice(head)}"
        )
    else:
        person = text.split(" ")[0]
        message(
            f"{random.choice(balls)}{random.choice(shaft)}{random.choice(head)}{random.choice(emission)} all over {person}'s {random.choice(bodypart)}"
        )
