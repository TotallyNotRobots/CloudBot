"""
utility.py

Provides a number of simple commands for working with strings.

Created By:
    - Luke Rogers <https://github.com/lukeroge>
    - Dabo Ross <https://github.com/daboross>

Special Thanks:
    - Fletcher Boyd <https://github.com/thenoodle68>

License: GPL v3
"""

from __future__ import annotations

import base64
import binascii
import codecs
import collections
import hashlib
import json
import random
import re
import urllib.parse
from typing import TYPE_CHECKING

from cloudbot import hook
from cloudbot.util import colors, formatting, web

if TYPE_CHECKING:
    from cloudbot.event_functions import EventNotice

COLORS = collections.OrderedDict(
    [
        ("red", "\x0304"),
        ("orange", "\x0307"),
        ("yellow", "\x0308"),
        ("green", "\x0309"),
        ("cyan", "\x0303"),
        ("ltblue", "\x0310"),
        ("rylblue", "\x0312"),
        ("blue", "\x0302"),
        ("magenta", "\x0306"),
        ("pink", "\x0313"),
        ("maroon", "\x0305"),
    ]
)

leet_text: dict[str, list[str]] = {}

# helper functions

strip_re = re.compile(r"[\u0003\u0002\u001F\u000F](?:,?\d{1,2}(?:,\d{1,2})?)?")


def strip(string):
    return strip_re.sub("", string)


def translate(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text


# on_start


@hook.on_start()
def load_text(bot) -> None:
    leet_text.clear()
    with open((bot.data_path / "leet.json"), encoding="utf-8") as f:
        leet_text.update(json.load(f))


# misc


@hook.command("qrcode", "qr")
def qrcode(text):
    """<link> - returns a link to a QR code image for <link>"""

    args = {
        "cht": "qr",  # chart type (QR)
        "chs": "200x200",  # dimensions
        "chl": text,  # data
    }

    argstring = urllib.parse.urlencode(args)

    link = f"http://chart.googleapis.com/chart?{argstring}"
    return web.try_shorten(link)


# basic text tools


@hook.command("capitalize", "capitalise")
def capitalize(text):
    """<string> - Capitalizes <string>."""
    return ". ".join([sentence.capitalize() for sentence in text.split(". ")])


@hook.command()
def upper(text):
    """<string> - Convert string to uppercase."""
    return text.upper()


@hook.command()
def lower(text):
    """<string> - Convert string to lowercase."""
    return text.lower()


@hook.command()
def titlecase(text):
    """<string> - Convert string to title case."""
    return text.title()


@hook.command()
def swapcase(text):
    """<string> - Swaps the capitalization of <string>."""
    return text.swapcase()


@hook.command("aesthetic", "vapor", "fw")
def fullwidth(text):
    """<string> - Converts <string> to full width characters."""
    HALFWIDTH_TO_FULLWIDTH = str.maketrans(
        '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&()*+,-./:;<=>?@[]^_`{|}~ ',
        "\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19\uff41\uff42\uff43\uff44\uff45\uff46\uff47\uff48\uff49\uff4a\uff4b\uff4c\uff4d\uff4e\uff4f\uff50\uff51\uff52\uff53\uff54\uff55\uff56\uff57\uff58\uff59\uff5a\uff21\uff22\uff23\uff24\uff25\uff26\uff27\uff28\uff29\uff2a\uff2b\uff2c\uff2d\uff2e\uff2f\uff30\uff31\uff32\uff33\uff34\uff35\uff36\uff37\uff38\uff39\uff3a\uff01\u309b\uff03\uff04\uff05\uff06\uff08\uff09\uff0a\uff0b\u3001\u30fc\u3002\uff0f\uff1a\uff1b\u3008\uff1d\u3009\uff1f\uff20\uff3b\uff3d\uff3e\uff3f\u2018\uff5b\uff5c\uff5d\uff5e\u3000",
    )
    return text.translate(HALFWIDTH_TO_FULLWIDTH)


# encoding


@hook.command("rot13")
def rot13_encode(text):
    """<string> - Encode <string> with rot13."""
    encoder = codecs.getencoder("rot-13")
    return encoder(text)[0]


@hook.command("base64")
def base64_encode(text):
    """<string> - Encode <string> with base64."""
    return base64.b64encode(text.encode()).decode()


@hook.command("debase64", "unbase64")
def base64_decode(text, notice: EventNotice):
    """<string> - Decode <string> with base64."""
    try:
        decoded = base64.b64decode(text.encode()).decode(errors="ignore")
    except binascii.Error:
        notice(f"Invalid base64 string '{text}'")
        return None

    if repr(decoded)[1:-1] != decoded:
        return f"Non printable characters detected in output, escaped output: {decoded!r}"

    return decoded


@hook.command("isbase64", "checkbase64")
def base64_check(text) -> str:
    """<string> - Checks if <string> is a valid base64 encoded string"""
    try:
        base64.b64decode(text.encode())
    except binascii.Error:
        return f"'{text}' is not a valid base64 encoded string"
    else:
        return f"'{text}' is a valid base64 encoded string"


@hook.command()
def unescape(text):
    """<string> - Unicode unescapes <string>."""
    decoder = codecs.getdecoder("unicode_escape")
    return " ".join(decoder(text)[0].splitlines())


@hook.command()
def escape(text):
    """<string> - Unicode escapes <string>."""
    encoder = codecs.getencoder("unicode_escape")
    return " ".join(encoder(text)[0].decode().splitlines())


# length


@hook.command()
def length(text) -> str:
    """<string> - Gets the length of <string>"""
    return f"The length of that string is {len(text)} characters."


# reverse


@hook.command()
def reverse(text):
    """<string> - Reverses <string>."""
    return text[::-1]


# hashing


@hook.command("hash")
def hash_command(text):
    """<string> - Returns hashes of <string>."""
    return ", ".join(
        f"{x}: {getattr(hashlib, x)(text.encode('utf-8')).hexdigest()}"
        for x in ["md5", "sha1", "sha256"]
    )


# novelty


@hook.command()
def munge(text):
    """<text> - Munges up <text>."""
    return formatting.munge(text)


@hook.command()
def leet(text):
    """<text> - Makes <text> more 1337h4x0rz."""
    output = "".join(
        random.choice(leet_text[ch]) if ch.isalpha() else ch
        for ch in text.lower()
    )
    return output


# Based on plugin by FurCode - <https://github.com/FurCode/RoboCop2>
@hook.command()
def derpify(text):
    """<text> - returns some amusing responses from your input."""
    string = text.upper()
    pick_the = random.choice(["TEH", "DA"])  # codespell:ignore teh
    pick_e = random.choice(["E", "3", "A"])
    pick_qt = random.choice(["?!?!??", "???!!!!??", "?!??!?", "?!?!?!???"])
    pick_ex = random.choice(
        ["1111!11", "1!11", "!!1!", "1!!!!111", "!1!111!1", "!11!111"]
    )
    pick_end = random.choice(["", "OMG", "LOL", "WTF", "WTF LOL", "OMG LOL"])
    rules = {
        "YOU'RE": "UR",
        "YOUR": "UR",
        "YOU": "U",
        "WHAT THE HECK": "WTH",  # codespell:ignore wth
        "WHAT THE HELL": "WTH",  # codespell:ignore wth
        "WHAT THE FUCK": "WTF",
        "WHAT THE": "WT",
        "WHAT": "WUT",
        "ARE": "R",
        "WHY": "Y",
        "BE RIGHT BACK": "BRB",
        "BECAUSE": "B/C",
        "OH MY GOD": "OMG",
        "O": "OH",
        "THE": pick_the,
        "TOO": "2",
        "TO": "2",
        "BE": "B",
        "CK": "K",
        "ING": "NG",
        "PLEASE": "PLS",
        "SEE YOU": "CYA",
        "SEE YA": "CYA",
        "SCHOOL": "SKOOL",  # codespell:ignore skool
        "AM": "M",
        "AM GOING TO": "IAM GOING TO",
        "THAT": "DAT",
        "ICK": "IK",
        "LIKE": "LIEK",  # codespell:ignore liek
        "HELP": "HALP",  # codespell:ignore halp
        "KE": "EK",
        "E": pick_e,
        "!": pick_ex,
        "?": pick_qt,
    }
    output = f"{translate(string, rules)} {pick_end}"

    return output


# colors
@hook.command()
def color_parse(text):
    """<text> - Parse colors and formatting in <text> using $(thing) syntax"""
    return colors.parse(text)


# colors - based on code by Reece Selwood - <https://github.com/hitzler/homero>
@hook.command()
def rainbow(text):
    """<text> - Gives <text> rainbow colors."""
    text = str(text)
    text = strip(text)
    col = list(COLORS.items())
    out = ""
    l = len(COLORS)
    for i, t in enumerate(text):
        if t == " ":
            out += t
        else:
            out += col[i % l][1] + t
    return out


@hook.command()
def wrainbow(text):
    """<text> - Gives each word in <text> rainbow colors."""
    text = str(text)
    col = list(COLORS.items())
    text = strip(text).split(" ")
    out = []
    l = len(COLORS)
    for i, t in enumerate(text):
        out.append(col[i % l][1] + t)
    return " ".join(out)


@hook.command()
def usa(text):
    """<text> - Makes <text> more patriotic."""
    text = strip(text)
    c = [COLORS["red"], "\x0300", COLORS["blue"]]
    l = len(c)
    out = ""
    for i, t in enumerate(text):
        out += c[i % l] + t
    return out


@hook.command()
def superscript(text):
    """<text> - Makes <text> superscript."""
    regular = "abcdefghijklmnoprstuvwxyzABDEGHIJKLMNOPRTUVW0123456789+-=()"
    super_script = "\u1d43\u1d47\u1d9c\u1d48\u1d49\u1da0\u1d4d\u02b0\u2071\u02b2\u1d4f\u02e1\u1d50\u207f\u1d52\u1d56\u02b3\u02e2\u1d57\u1d58\u1d5b\u02b7\u02e3\u02b8\u1dbb\u1d2c\u1d2e\u1d30\u1d31\u1d33\u1d34\u1d35\u1d36\u1d37\u1d38\u1d39\u1d3a\u1d3c\u1d3e\u1d3f\u1d40\u1d41\u2c7d\u1d42\u2070\xb9\xb2\xb3\u2074\u2075\u2076\u2077\u2078\u2079\u207a\u207b\u207c\u207d\u207e"
    result = []
    for char in text:
        index = regular.find(char)
        if index != -1:
            result.append(super_script[index])
        else:
            result.append(char)
    return "".join(result)
