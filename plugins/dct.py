# dict.cc interface
#
# dict.c bot: pip install dict.cc.py

import logging

from dictcc import AVAILABLE_LANGUAGES, Dict

from cloudbot import hook

next_msg = "  ----- Type `.tn` for more translations"
logger = logging.getLogger("cloudbot")

last_results = {}  # per user results
translator = Dict()


@hook.command("t")
def dcc(text, nick):
    """t <in> <out> <query> - translate <query> from <in> to <out> where <in> and <out> are two-letter language codes"""
    global last_results
    text = text.strip().split()
    if len(text) < 3:
        return "Usage: .t <in> <out> <query>"
    inp = text[0]
    out = text[1]
    query = " ".join(text[2:])

    if inp not in AVAILABLE_LANGUAGES:
        return f"Invalid input language: {inp}"
    if out not in AVAILABLE_LANGUAGES:
        return f"Invalid output language: {out}"

    results = translator.translate(query, from_language=inp, to_language=out)
    logger.info(results)
    if len(results.translation_tuples) == 0:
        return "No transations were found!"
    result = results.translation_tuples.pop(0)
    last_results[nick] = results
    return f"\x02{results.from_lang.strip()}\x02: {result[0]} --> \x02{results.to_lang}\x02: {result[1]}{next_msg if len(last_results[nick].translation_tuples) > 0 else ''}"


@hook.command("tn")
def dcc_next(text, nick):
    global last_results
    results = last_results[nick]
    result = results.translation_tuples.pop(0)
    if last_results:
        return f"\x02{results.from_lang.strip()}\x02: {result[0]} --> \x02{results.to_lang}\x02: {result[1]}{next_msg if len(last_results[nick].translation_tuples) > 0 else ''}"
    else:
        return "No translations left!"
