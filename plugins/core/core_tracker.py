# plugin to keep track of bot state

import logging
from collections import deque

from cloudbot import hook

logger = logging.getLogger("cloudbot")


# functions called for bot state tracking


def bot_left_channel(conn, chan):
    logger.info("[%s|tracker] Bot left channel %r", conn.name, chan)
    if chan in conn.channels:
        conn.channels.remove(chan)
    if chan in conn.history:
        del conn.history[chan]


def bot_joined_channel(conn, chan):
    logger.info("[%s|tracker] Bot joined channel %r", conn.name, chan)
    if chan not in conn.channels:
        conn.channels.append(chan)

    conn.history[chan] = deque(maxlen=100)


@hook.irc_raw("KICK")
async def on_kick(conn, chan, target, loop):
    # if the bot has been kicked, remove from the channel list
    if target == conn.nick:
        bot_left_channel(conn, chan)
        if conn.config.get("auto_rejoin", False):
            loop.call_later(5, conn.join, chan)
            loop.call_later(
                5,
                logger.info,
                "[%s|tracker] Bot was kicked from %s, rejoining channel.",
                conn.name,
                chan,
            )


@hook.irc_raw("NICK")
async def on_nick(irc_paramlist, conn, nick):
    old_nick = nick
    new_nick = str(irc_paramlist[0])

    if old_nick == conn.nick:
        conn.nick = new_nick
        logger.info(
            "[%s|tracker] Bot nick changed from %r to %r.",
            conn.name,
            old_nick,
            new_nick,
        )


# for channels the host tells us we're joining without us joining it ourselves
# mostly when using a BNC which saves channels
@hook.irc_raw("JOIN")
async def on_join(conn, chan, nick):
    if nick == conn.nick:
        bot_joined_channel(conn, chan)


@hook.irc_raw("PART")
async def on_part(conn, chan, nick):
    if nick == conn.nick:
        bot_left_channel(conn, chan)
