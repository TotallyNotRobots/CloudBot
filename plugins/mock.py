from cloudbot import hook


def get_latest_line(text, conn, chan, nick):
    for name, _, msg in reversed(conn.history.get(chan.casefold(), [])):
        if nick.casefold() == name.casefold():
            # Ignore commands
            if msg.startswith(conn.config["command_prefix"]):
                continue
            if not text:
                return msg
            elif text in msg:
                return msg

    return None


@hook.command()
def mock(text, chan, conn, message):
    """<nick> - turn <user>'s last message in to aLtErNaTiNg cApS"""
    nick, text, *_ = text.strip().split(None, 1) + ["", ""]
    line = get_latest_line(text, conn, chan, nick)
    if line is None:
        return f"Nothing found in recent history for {nick}"

    if line.startswith("\x01ACTION"):
        fmt = "* {nick} {msg}"
        line = line[8:].strip(" \x01")
    else:
        fmt = "<{nick}> {msg}"

    # Return the message in aLtErNaTiNg cApS
    line = "".join(
        c.upper() if i & 1 else c.lower() for i, c in enumerate(line)
    )
    message(fmt.format(nick=nick, msg=line))
    return None
