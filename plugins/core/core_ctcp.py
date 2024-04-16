import datetime

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
            # Bot should return exactly what the user sends as the ping parameter
            notice(f"\x01PING {params}\x01")
        elif command == "TIME":
            # General convention is to return the asc time
            notice(f"\x01TIME {datetime.datetime.now().ctime()}\x01")
