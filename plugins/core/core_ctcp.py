import time

import cloudbot
from cloudbot import hook
from cloudbot.event import EventType


# CTCP responses
@hook.event([EventType.other])
async def ctcp_version(notice, irc_ctcp_text):
    if irc_ctcp_text:
        command, _, params = irc_ctcp_text.partition(" ")
        if command == "VERSION":
            notice(
                "\x01VERSION gonzobot a fork of Cloudbot {} - https://snoonet.org/gonzobot\x01".format(
                    cloudbot.__version__
                )
            )
        elif command == "PING":
            notice(
                "\x01PING {}\x01".format(params)
            )  # Bot should return exactly what the user sends as the ping parameter
        elif command == "TIME":
            notice(
                "\x01TIME {}\x01".format(time.asctime())
            )  # General convention is to return the asc time
