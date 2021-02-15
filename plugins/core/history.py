import time
from collections import deque

from cloudbot import hook
from cloudbot.event import EventType


def track_history(event, message_time, conn):
    try:
        history = conn.history[event.chan]
    except KeyError:
        conn.history[event.chan] = deque(maxlen=100)
        # what are we doing here really
        # really really
        history = conn.history[event.chan]

    data = (event.nick, message_time, event.content)
    history.append(data)


@hook.event([EventType.message, EventType.action], singlethread=True)
def chat_tracker(event, conn):
    if event.type is EventType.action:
        event.content = "\x01ACTION {}\x01".format(event.content)

    message_time = time.time()
    track_history(event, message_time, conn)


@hook.command(autohelp=False)
async def resethistory(event, conn):
    """- resets chat history for the current channel"""
    try:
        conn.history[event.chan].clear()
        return "Reset chat history for current channel."
    except KeyError:
        # wat
        return "There is no history for this channel."
