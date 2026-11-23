from __future__ import annotations

import re
from enum import Enum, unique
from typing import TYPE_CHECKING

from cloudbot import hook
from cloudbot.util import textgen

if TYPE_CHECKING:
    from collections.abc import Callable

    from cloudbot.bot import CloudBot
    from cloudbot.client import Client
    from cloudbot.event_functions import (
        EventAction,
        EventIsNickValid,
        EventMessage,
        EventReply,
    )


@unique
class RespType(Enum):
    ACTION = 1
    MESSAGE = 2
    REPLY = 3


def is_self(conn: Client, target):
    """Checks if a string is "****self" or contains conn.name."""
    return bool(
        re.search(f"(^..?.?.?self|{re.escape(conn.nick)})", target, re.I)
    )


attack_data = dict[str, textgen.TemplateConfig]()


class BasicAttack:
    def __init__(
        self,
        name: str,
        doc: str,
        *commands: str,
        action: str | None = None,
        file: str | None = None,
        response: RespType = RespType.ACTION,
        require_target: bool = True,
    ) -> None:
        self.name: str = name
        self.action: str = action or name
        self.doc: str = doc
        self.commands: tuple[str, ...] = commands or (name,)
        if file is None:
            file = f"{name}.json"

        self.file: str = file
        self.response: RespType = response
        self.require_target: bool = require_target


ATTACKS = (
    BasicAttack("lart", "<user> - LARTs <user>"),
    BasicAttack(
        "flirt",
        "<user> - flirts with <user>",
        "flirt",
        "sexup",
        "jackmeoff",
        action="flirt with",
        response=RespType.MESSAGE,
    ),
    BasicAttack("kill", "<user> - kills <user>", "kill", "end"),
    BasicAttack("slap", "<user> - Makes the bot slap <user>."),
    BasicAttack(
        "compliment",
        "<user> - Makes the bot compliment <user>.",
        response=RespType.MESSAGE,
    ),
    BasicAttack(
        "strax",
        "[user] - Generates a quote from Strax, optionally targeting [user]",
        action="attack",
        response=RespType.MESSAGE,
        require_target=False,
    ),
    BasicAttack(
        "nk",
        "- outputs a random North Korea propaganda slogan",
        action="target",
        response=RespType.MESSAGE,
        require_target=False,
    ),
    BasicAttack(
        "westworld",
        "- Westworld quotes",
        action="target",
        response=RespType.MESSAGE,
        require_target=False,
    ),
    BasicAttack("insult", "<user> - insults <user>", response=RespType.MESSAGE),
    BasicAttack(
        "present",
        "<user> - gives gift to <user>",
        "present",
        "gift",
        action="give a gift to",
    ),
    BasicAttack("spank", "<user> - Spanks <user>"),
    BasicAttack(
        "bdsm", "<user> - Just a little bit of kinky fun.", "bdsm", "dominate"
    ),
    BasicAttack("clinton", "<user> - Clinton a <user>"),
    BasicAttack("trump", "<user> - Trump a <user>"),
    BasicAttack("glomp", "<user> - glomps <user>"),
    BasicAttack("bite", "<user> - bites <user>"),
    BasicAttack(
        "lurve",
        "<user> - lurves <user>",
        "lurve",
        "luff",
        "luv",
        response=RespType.MESSAGE,
    ),
    BasicAttack("hug", "<user> - hugs <user>", response=RespType.MESSAGE),
    BasicAttack(
        "highfive",
        "<user> - highfives <user>",
        "high5",
        "hi5",
        "highfive",
        response=RespType.MESSAGE,
    ),
    BasicAttack(
        "fight",
        "<user> - fights <user>",
        "fight",
        "fite",
        "spar",
        "challenge",
        response=RespType.MESSAGE,
    ),
    BasicAttack(
        "pokemon",
        "<user> - uses a pok\xe9mon on <user>",
        response=RespType.MESSAGE,
    ),
    BasicAttack(
        "stab", "<user> - stabs <user> in a random body part with random weapon"
    ),
)


@hook.on_start()
def load_attacks(bot: CloudBot) -> None:
    attack_data.clear()
    data_dir = bot.data_path / "attacks"
    for data_file in ATTACKS:
        attack_data[data_file.name] = textgen.TemplateConfig.from_json_file(
            data_dir / data_file.file
        )


def basic_format(
    nick: str, text: str, data: textgen.TemplateConfig, **kwargs: str
) -> str:
    user = text
    kwargs["user"] = user
    kwargs["target"] = user
    kwargs["nick"] = nick

    generator = data.make_generator(has_target=bool(text), variables=kwargs)
    return generator.generate_string()


def basic_attack(attack: BasicAttack) -> Callable[..., str | None]:
    def func(
        text: str,
        conn: Client,
        nick: str,
        action: EventAction,
        message: EventMessage,
        reply: EventReply,
        is_nick_valid: EventIsNickValid,
    ) -> str | None:
        responses = {
            RespType.ACTION: action,
            RespType.REPLY: reply,
            RespType.MESSAGE: message,
        }

        target = text
        if target:
            if not is_nick_valid(target):
                return f"I can't {attack.action} that."

            if is_self(conn, target):
                target = nick
                nick = conn.nick

        out = basic_format(nick, target, attack_data[attack.name])

        responses[attack.response](out)
        return None

    func.__name__ = attack.name
    func.__doc__ = attack.doc
    return func


def create_basic_hooks() -> None:
    for attack in ATTACKS:
        globals()[attack.name] = hook.command(
            *attack.commands, autohelp=attack.require_target
        )(basic_attack(attack))


create_basic_hooks()
