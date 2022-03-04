import json
import re
from collections import defaultdict
from enum import Enum, unique
from typing import Any, Dict

from cloudbot import hook
from cloudbot.util import textgen


@unique
class RespType(Enum):
    ACTION = 1
    MESSAGE = 2
    REPLY = 3


def is_self(conn, target):
    """Checks if a string is "****self" or contains conn.name."""
    return bool(
        re.search(
            "(^..?.?.?self|{})".format(re.escape(conn.nick)), target, re.I
        )
    )


attack_data: Dict[str, Dict[str, Any]] = defaultdict(dict)


class BasicAttack:
    def __init__(
        self,
        name,
        doc,
        *commands,
        action=None,
        file=None,
        response=RespType.ACTION,
        require_target=True,
    ):
        self.name = name
        self.action = action or name
        self.doc = doc
        self.commands = commands or [name]
        if file is None:
            file = "{}.json".format(name)

        self.file = file
        self.response = response
        self.require_target = require_target


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
        "<user> - uses a pokémon on <user>",
        response=RespType.MESSAGE,
    ),
    BasicAttack(
        "stab", "<user> - stabs <user> in a random body part with random weapon"
    ),
)


def load_data(path, data_dict):
    data_dict.clear()
    with path.open(encoding="utf-8") as f:
        data_dict.update(json.load(f))


@hook.on_start()
def load_attacks(bot):
    attack_data.clear()
    data_dir = bot.data_path / "attacks"
    for data_file in ATTACKS:
        load_data(data_dir / data_file.file, attack_data[data_file.name])


def basic_format(nick, text, data, **kwargs):
    user = text
    kwargs["user"] = user
    kwargs["target"] = user
    kwargs["nick"] = nick

    if text:
        try:
            templates = data["target_templates"]
        except KeyError:
            templates = data["templates"]
    else:
        templates = data["templates"]

    generator = textgen.TextGenerator(
        templates, data.get("parts", {}), variables=kwargs
    )

    return generator.generate_string()


def basic_attack(attack):
    def func(text, conn, nick, action, message, reply, is_nick_valid):
        responses = {
            RespType.ACTION: action,
            RespType.REPLY: reply,
            RespType.MESSAGE: message,
        }

        target = text
        if target:
            if not is_nick_valid(target):
                return "I can't {action} that.".format(action=attack.action)

            if is_self(conn, target):
                target = nick
                nick = conn.nick

        out = basic_format(nick, target, attack_data[attack.name])

        responses[attack.response](out)
        return None

    func.__name__ = attack.name
    func.__doc__ = attack.doc
    return func


def create_basic_hooks():
    for attack in ATTACKS:
        globals()[attack.name] = hook.command(
            *attack.commands, autohelp=attack.require_target
        )(basic_attack(attack))


create_basic_hooks()
