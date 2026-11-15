from __future__ import annotations

import random
from typing import TYPE_CHECKING

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot
    from cloudbot.event_functions import EventMessage

fmklist: list[str] = []


@hook.on_start()
def load_fmk(bot: CloudBot) -> None:
    fmklist.clear()
    with open(bot.data_path / "fmk.txt", encoding="utf-8") as f:
        fmklist.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@hook.command("fmk", autohelp=False)
def fmk(text, message: EventMessage) -> None:
    """[nick] - Fuck, Marry, Kill"""
    message(
        " {} FMK - {}, {}, {}".format(
            (text.strip() if text.strip() else ""),
            random.choice(fmklist),
            random.choice(fmklist),
            random.choice(fmklist),
        )
    )
