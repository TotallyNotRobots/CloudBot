import datetime

import cloudbot
from cloudbot import hook
from cloudbot.event import EventType

# CTCP responses
VERSION = (
    "gonzobot a fork of Cloudbot {} - "
    "https://snoonet.org/gonzobot".format(cloudbot.__version__)
)


def nctcp(event, cmd, msg):
    event.notice("\x01{} {}\x01".format(cmd, msg))


@hook.event([EventType.other])
def ctcp_version(irc_ctcp_text, event):
    if not irc_ctcp_text:
        return

    command, _, params = irc_ctcp_text.partition(" ")
    if command == "VERSION":
        nctcp(event, command, VERSION)
    elif command == "PING":
        # Bot should return exactly what the user sends as the ping parameter
        nctcp(event, command, params)
    elif command == "TIME":
        # General convention is to return the ctime format
        nctcp(event, command, datetime.datetime.now().ctime())
