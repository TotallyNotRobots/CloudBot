import re

from cloudbot import hook
from cloudbot.util.formatting import ireplace

correction_re = re.compile(r"^[sS]/(.+)/(.+)(?:/(.+)?)?$")

unescape_re = re.compile(r"\\(.)")

@hook.regex(correction_re)
def correction(match, conn, nick, chan, message):
    groups = [unescape_re.sub(r"\1", group or "") for group in match.groups()]
    find = groups[0]
    replace = groups[1]

    for name, timestamp, msg in reversed(conn.history[chan]):
        if correction_re.match(msg):
            # don't correct corrections, it gets really confusing
            continue

        new = re.sub(find, replace, msg, flags=re.I)
        if new:
            message("Correction, {}".format(fmt.format(name, new)))

            if nick.lower() == name.lower():
                msg = ireplace(re.escape(msg), find_esc, replace_esc)
                msg = unescape_re.sub(r"\1", msg)
                conn.history[chan].append((name, timestamp, msg))

            break

    return None
