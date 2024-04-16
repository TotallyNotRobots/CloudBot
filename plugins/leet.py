import unidecode

from cloudbot import hook

origspace = "abcdefghijklmnopqrstuvwxyz"
keyspace = "4bcd3fg8ijk1mn0pqr57uvwxy2"


def leetify(text):
    out = ""
    text = unidecode.unidecode(text)
    for origc in text:
        if origc in origspace:
            out += keyspace[origspace.index(origc)]
        else:
            out += origc
    return out


@hook.command("leet", "leetify", "l33t", "1337")
def leet(text, chan, bot, conn, message):
    """<text> - Converts text to leet"""
    if text.strip().split()[0] == text:
        max_i = 1000
        i = 0
        for name, _timestamp, msg in reversed(conn.history[chan]):
            if i == 0:
                i += 1
                continue
            if i >= max_i:
                break
            i += 1

            if msg.startswith("\x01ACTION"):
                mod_msg = msg[7:].strip(" \x01")
                fmt = "* {} {}"
            else:
                mod_msg = msg
                fmt = "<{}> {}"
            if name.casefold() == text.strip().casefold():
                message(fmt.format(name, leetify(mod_msg)))
                return
    return leetify(text)
