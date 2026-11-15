from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.event_functions import EventMessage

deal_with_it_phrases = [
    "Stop complaining, \x02{}\x02, and",
    "Jesus fuck \x02{}\x02, just",
    "Looks like \x02{}\x02 needs to",
    "Ever think that \x02{}\x02 just needs to",
]
reaction_macros: dict[str, list[str]] = {}


@hook.on_start()
def load_macros(bot) -> None:
    reaction_macros.clear()
    with open(
        (bot.data_path / "reaction_macros.json"), encoding="utf-8"
    ) as macros:
        reaction_macros.update(json.load(macros))


@hook.command("dwi", "dealwithit")
def deal_with_it(text, message: EventMessage) -> None:
    """<nick> - Tell <nick> in the channel to deal with it. Code located in reactions.py"""
    person_needs_to_deal = text.strip()
    phrase = random.choice(deal_with_it_phrases)
    formated_phrase = phrase.format(person_needs_to_deal)
    message(
        f"{formated_phrase} {random.choice(reaction_macros['deal_with_it_macros'])}"
    )


@hook.command("fp", "facepalm")
def face_palm(text, message: EventMessage) -> None:
    """<nick> - Expresses your frustration with <Nick>. Code located in reactions.py"""
    face_palmer = text.strip()
    message(
        f"Dammit {face_palmer} {random.choice(reaction_macros['facepalm_macros'])}"
    )


@hook.command("hd", "headdesk")
def head_desk(text, message: EventMessage) -> None:
    """<nick> - Hit your head against the desk becausae of <nick>. Code located in reactions.py"""
    idiot = text.strip()
    message(f"{idiot} {random.choice(reaction_macros['head_desk_macros'])}")


@hook.command("fetish", "tmf")
def my_fetish(text, message: EventMessage) -> None:
    """<nick> - Did some one just mention what your fetish was? Let <nick> know! Code located in reactions.py"""
    person_to_share_fetish_with = text.strip()
    message(
        f"{person_to_share_fetish_with} {random.choice(reaction_macros['fetish_macros'])}"
    )
