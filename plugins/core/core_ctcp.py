from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

import cloudbot
from cloudbot import hook
from cloudbot.event import EventType

if TYPE_CHECKING:
    from cloudbot.event_functions import EventNotice


# CTCP responses
@hook.event([EventType.other])
async def ctcp_version(notice: EventNotice, irc_ctcp_text) -> None:
    if irc_ctcp_text:
        command, _, params = irc_ctcp_text.partition(" ")
        if command == "VERSION":
            notice(
                f"\x01VERSION gonzobot a fork of Cloudbot {cloudbot.__version__} - https://snoonet.org/gonzobot\x01"
            )
        elif command == "PING":
            # Bot should return exactly what the user sends as the ping parameter
            notice(f"\x01PING {params}\x01")
        elif command == "TIME":
            # General convention is to return the asc time
            notice(f"\x01TIME {dt.datetime.now().ctime()}\x01")
