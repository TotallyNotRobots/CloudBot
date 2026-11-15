from __future__ import annotations

import re
from typing import TYPE_CHECKING

from cloudbot import hook
from cloudbot.util.formatting import ireplace

if TYPE_CHECKING:
    from cloudbot.client import Client
    from cloudbot.event_functions import EventMessage

correction_re = re.compile(
    r"^[sS]/(?:(.*?)(?<!\\)/(.*?)(?:(?<!\\)/([igx]{,4}))?)\s*$"
)
unescape_re = re.compile(r"\\(.)")


@hook.regex(correction_re)
def correction(match, conn: Client, nick, chan, message: EventMessage):
    groups = [unescape_re.sub(r"\1", group or "") for group in match.groups()]
    find = groups[0]
    replace = groups[1]
    if find == replace:
        return f"really dude? you want me to replace {find} with {replace}?"

    if not find.strip():
        # Replacing empty or entirely whitespace strings is spammy
        return f"really dude? you want me to replace nothing with {replace}?"

    for name, timestamp, msg in reversed(conn.history[chan]):
        if correction_re.match(msg):
            # don't correct corrections, it gets really confusing
            continue

        if find.lower() in msg.lower():
            find_esc = re.escape(find)
            replace_esc = re.escape(replace)
            if msg.startswith("\x01ACTION"):
                mod_msg = msg[7:].strip(" \x01")
                fmt = "* {} {}"
            else:
                mod_msg = msg
                fmt = "<{}> {}"

            mod_msg = ireplace(
                re.escape(mod_msg), find_esc, f"\x02{replace_esc}\x02"
            )

            mod_msg = unescape_re.sub(r"\1", mod_msg)

            message(f"Correction, {fmt.format(name, mod_msg)}")

            if nick.lower() == name.lower():
                msg = ireplace(re.escape(msg), find_esc, replace_esc)
                msg = unescape_re.sub(r"\1", msg)
                conn.history[chan].append((name, timestamp, msg))

            break

    return None
