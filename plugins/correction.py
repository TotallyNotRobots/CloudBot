import re

from cloudbot import hook
from cloudbot.util.formatting import ireplace

correction_re = re.compile(
    r"^(?:[sS]/(?:((?:\\/|[^/])*?)(?<!\\)/((?:\\/|[^/])*?)(?:(?<!\\)/([igx]{,4}))?)\s*?;*?)(?:;\s*?[sS]/(?:((?:\\/|[^/])*?)(?<!\\)/((?:\\/|[^/])*?)(?:(?<!\\)/([igx]{,4}))?)\s*?;*?)*?$"
)
exp_re = re.compile(
    r"(?:[sS]/(?:((?:\\/|[^/])*)(?<!\\)/((?:\\/|[^/])*)(?:(?<!\\)/([igx]{,4}))?))"
)
unescape_re = re.compile(r"\\(.)")

LAMESIZE = 15

REFLAGS = {
    "i": re.IGNORECASE,
    "g": re.MULTILINE,
    "x": re.VERBOSE,
}


def get_flags(flags, message):
    re_flags = []
    for flag in flags:
        if flag not in "igx":
            message(
                "Invalid regex flag `{}`. Valid are: [{}]".format(
                    flag, ", ".join(REFLAGS.keys())
                )
            )
        re_flags.append(REFLAGS[flag])
    return re_flags


def paser_sed_exp(groups, message):
    find = groups[0]
    replace = groups[1] if groups[1] else ""
    flags = str(groups[2]) if groups[2] else ""
    return find, replace, get_flags(flags, message)


@hook.regex(correction_re)
def correction(match, conn, nick, chan, message):
    # groups = [unescape_re.sub(r"\1", group or "") for group in match.groups()]
    find, replace, re_flags = paser_sed_exp(match.groups(), message)
    # if find doesn't have any special character and find is smaller than replace we yell at the user
    if not re.search(r"[\.\+\[\]\(\)\{\}\^\$\|]", find) and len(
        find
    ) + LAMESIZE < len(replace):
        message(
            f"<{nick}>: Your find is much shorter than your replace and you didn't even use proper regex. Stop trying to do lame stuff and send a proper message again if you need to!"
        )
        return

    max_i = 50000
    i = 0

    for name, _timestamp, msg in reversed(conn.history[chan]):
        if i >= max_i:
            break
        i += 1
        if correction_re.match(msg):
            # don't correct corrections, it gets really confusing
            continue

        if msg.startswith("\x01ACTION"):
            mod_msg = msg[7:].strip(" \x01")
            fmt = "* {} {}"
        else:
            mod_msg = msg
            fmt = "<{}> {}"

        new = re.sub(
            find,
            "\x02" + replace + "\x02",
            mod_msg,
            count=re.MULTILINE not in re_flags,
            flags=sum(re_flags),
        )
        if new != mod_msg:
            find_esc = re.escape(find)
            replace_esc = re.escape(new)
            mod_msg = unescape_re.sub(r"\1", new)
            print(f"{exp_re=}")
            print(f"{match[0]=}")
            for exp in re.findall(exp_re, match[0])[1:]:
                if not exp:
                    continue
                print(f"{exp=}")
                find, replace, flags = exp
                print(f"{find=}")
                print(f"{replace=}")
                re_flags = get_flags(flags, message)
                new = re.sub(
                    find,
                    "\x02" + replace + "\x02",
                    mod_msg,
                    count=re.MULTILINE not in re_flags,
                    flags=sum(re_flags),
                )
                find_esc = re.escape(find)
                replace_esc = re.escape(new)
                mod_msg = unescape_re.sub(r"\1", new)

            mod_msg = ireplace(
                re.escape(mod_msg), find_esc, "\x02" + replace_esc + "\x02"
            )

            mod_msg = unescape_re.sub(r"\1", mod_msg)

            message(f"Correction, {fmt.format(name, mod_msg)}")

            if nick.lower() == name.lower():
                msg = ireplace(re.escape(msg), find_esc, replace_esc)
                msg = unescape_re.sub(r"\1", msg)
                conn.history[chan].append((name, timestamp, msg))

            break

    else:
        return "No match"
