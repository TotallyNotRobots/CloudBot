from __future__ import annotations

import secrets
import string
from typing import TYPE_CHECKING

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot
    from cloudbot.event_functions import EventNotice

gen = secrets.SystemRandom()
common_words: list[str] = []


@hook.on_start()
def load_words(bot: CloudBot) -> None:
    new_words: list[str] = []
    with open(bot.data_path / "password_words.txt", encoding="utf-8") as f:
        new_words = [line.strip() for line in f.readlines()]

    common_words.clear()
    common_words.extend(new_words)


@hook.command(autohelp=False)
def password(text, notice: EventNotice) -> None:
    """[length [types]] - generates a password of <length> (default 12).
    [types] can include 'alpha', 'no caps', 'numeric', 'symbols' or any combination: eg. 'numbers symbols'
    (default: alpha numeric no caps)"""
    okay = ""

    # find the length needed for the password
    numb = text.split(" ")

    try:
        length = int(numb[0])
    except ValueError:
        length = 12

    if length > 50:
        notice("Maximum length is 50 characters.")
        return

    # add alpha characters
    if "alpha" in text or "letter" in text:
        okay += string.ascii_lowercase
        # adds capital characters if not told not to
        if "no caps" not in text:
            okay += string.ascii_uppercase

    # add numbers
    if "numeric" in text or "number" in text:
        okay += string.digits

    # add symbols
    if "symbol" in text or "special" in text:
        okay += string.punctuation

    # defaults to lowercase alpha + numbers password if the okay string is empty
    if not okay:
        okay = string.ascii_lowercase + string.digits

    _okay = list(okay)

    # extra random lel
    gen.shuffle(_okay)
    chars = []

    for _ in range(length):
        chars.append(gen.choice(_okay))

    notice("".join(chars))


@hook.command("wpass", "wordpass", "wordpassword", autohelp=False)
def word_password(text, notice: EventNotice) -> None:
    """[length] - generates an easy to remember password with [length] (default 4) commonly used words"""
    try:
        length = int(text)
    except ValueError:
        length = 3

    if length > 10:
        notice("Maximum length is 50 characters.")
        return

    words = []
    # generate password
    for _ in range(length):
        words.append(gen.choice(common_words))

    notice(
        f"Your password is '{' '.join(words)}'. Feel free to remove the spaces when using it."
    )
