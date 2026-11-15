from __future__ import annotations

from typing import TYPE_CHECKING

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.client import Client
    from cloudbot.event_functions import EventMessage


def get_latest_line(conn: Client, chan, nick):
    for name, _, msg in reversed(conn.history.get(chan.casefold(), [])):
        if nick.casefold() == name.casefold():
            return msg

    return None


@hook.command()
def mock(text, chan, conn: Client, message: EventMessage):
    """<nick> - turn <user>'s last message in to aLtErNaTiNg cApS"""
    nick = text.strip()
    line = get_latest_line(conn, chan, nick)
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
