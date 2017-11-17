from cloudbot import hook


def get_latest_line(conn, chan, nick):
    for name, timestamp, msg in reversed(conn.history[chan.casefold()]):
        if nick.casefold() == name.casefold():
            return msg

    return None


@hook.command
def mock(text, chan, conn, message):
    nick = text.strip()
    line = get_latest_line(conn, chan, nick)
    if line is None:
        return "Nothing found in recent history for {}".format(nick)

    if line.startswith("\x01ACTION"):
        fmt = "* {} {}"
        line = line[8:].strip(' \x01')
    else:
        fmt = "<{}> {}"

    line = "".join(c.upper() if i & 1 else c for i, c in enumerate(line))
    message(fmt.format(nick, line))
