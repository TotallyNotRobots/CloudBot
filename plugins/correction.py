import re

from cloudbot import hook
from cloudbot.util.formatting import ireplace

correction_re = re.compile(
    r"^[sS]/(?:(.*?)(?<!\\)/(.*?)(?:(?<!\\)/([igx]{,4}))?)\s*$"
)
unescape_re = re.compile(r"\\(.)")


@hook.regex(correction_re)
def correction(match, conn, nick, chan, message):
    groups = [unescape_re.sub(r"\1", group or "") for group in match.groups()]
    find = groups[0]
    replace = groups[1]
    if find == replace:
        return "really dude? you want me to replace {} with {}?".format(
            find, replace
        )

    if not find.strip():
        # Replacing empty or entirely whitespace strings is spammy
        return "really dude? you want me to replace nothing with {}?".format(
            replace
        )

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
                re.escape(mod_msg), find_esc, "\x02" + replace_esc + "\x02"
            )

            mod_msg = unescape_re.sub(r"\1", mod_msg)

            message("Correction, {}".format(fmt.format(name, mod_msg)))

            if nick.lower() == name.lower():
                msg = ireplace(re.escape(msg), find_esc, replace_esc)
                msg = unescape_re.sub(r"\1", msg)
                conn.history[chan].append((name, timestamp, msg))

            break

    return None
