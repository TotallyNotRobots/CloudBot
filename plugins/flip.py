import random
from typing import Dict, Optional

from cloudbot import hook
from cloudbot.util import formatting

FIXED_TABLE = "\u252c\u2500\u252c\u30ce(\u0ca0_\u0ca0\u30ce)"

FLIP_CHAR = " \ufe35 "

table_status: Dict[str, Optional[bool]] = {}

replacements = {
    "a": "\u0250",
    "b": "q",
    "c": "\u0254",
    "d": "p",
    "e": "\u01dd",
    "f": "\u025f",
    "g": "\u0183",
    "h": "\u0265",
    "i": "\u1d09",
    "j": "\u027e",
    "k": "\u029e",
    "l": "\u05df",
    "m": "\u026f",
    "n": "u",
    "o": "o",
    "p": "d",
    "q": "b",
    "r": "\u0279",
    "s": "s",
    "t": "\u0287",
    "u": "n",
    "v": "\u028c",
    "w": "\u028d",
    "x": "x",
    "y": "\u028e",
    "z": "z",
    "?": "\\xbf",
    ".": "\u02d9",
    ",": "'",
    "(": ")",
    "<": ">",
    "[": "]",
    "{": "}",
    "'": ",",
    "_": "\u203e",
    "\u0250": "a",
    "\u0254": "c",
    "\u01dd": "e",
    "\u025f": "f",
    "\u0183": "g",
    "\u0265": "h",
    "\u1d09": "i",
    "\u027e": "j",
    "\u029e": "k",
    "\u05df": "l",
    "\u026f": "m",
    "\u0279": "r",
    "\u0287": "t",
    "\u028c": "v",
    "\u028d": "w",
    "\u028e": "y",
    "\\xbf": "?",
    "\u02d9": ".",
    ")": "(",
    ">": "<",
    "]": "[",
    "}": "{",
    "\u203e": "_",
}


# append an inverted form of replacements to itself, so flipping works both ways
replacements.update(dict((v, k) for k, v in replacements.items()))

flippers = [
    "( \uff89\u2299\ufe35\u2299\uff09\uff89",
    "(\u256f\xb0\u25a1\xb0\uff09\u256f",
    "( \uff89\u2649\ufe35\u2649 \uff09\uff89",
]

table_flipper = "\u253b\u2501\u253b \ufe35\u30fd(`\u0414\xb4)\uff89\ufe35 \u253b\u2501\u253b"


@hook.command()
def flip(text, message, chan):
    """<text> - Flips <text> over."""
    if text in ["table", "tables"]:
        message(
            random.choice(
                [
                    random.choice(flippers) + FLIP_CHAR + "\u253B\u2501\u253B",
                    table_flipper,
                ]
            )
        )
        table_status[chan] = True
    elif text == "5318008":
        out = "BOOBIES"
        message(random.choice(flippers) + FLIP_CHAR + out)
    elif text == "BOOBIES":
        out = "5318008"
        message(random.choice(flippers) + FLIP_CHAR + out)
    else:
        message(
            random.choice(flippers)
            + FLIP_CHAR
            + formatting.multi_replace(text[::-1], replacements)
        )


@hook.command()
def table(text, message):
    """<text> - Flip text"""
    message(
        random.choice(flippers)
        + FLIP_CHAR
        + formatting.multi_replace(text[::-1].lower(), replacements)
    )


@hook.command()
def fix(text, message, chan):
    """<text> - fixes a flipped over table."""
    if text in ["table", "tables"]:
        if table_status.pop(chan, False) is True:
            message(FIXED_TABLE)
        else:
            message(
                "no tables have been turned over in {}, thanks for checking!".format(
                    chan
                )
            )
    else:
        flip(text, message, chan)
