import asyncio
import time

from cloudbot import hook
from cloudbot.util import colors


@hook.command(autohelp=False, permissions=["botcontrol"])
def conncheck(nick, bot, notice):
    """- This command is an effort to make the bot reconnect to a network if it has been disconnected."""
    # For each irc network return a notice on the connection state and send a message from
    # each connection to the nick that used the command.
    for conn in bot.connections:
        # I am not sure if the connected property is ever changed.
        notice("{}, {}".format(conn, bot.connections[conn].connected))
        # if the value is in fact false try to connect
        if not bot.connections[conn].connected:
            bot.connections[conn].try_connect()
        # Send a message from each irc network connection to the nick that issued the command
        bot.connections[conn].message(nick, "just letting you know I am here. {}".format(conn))


@asyncio.coroutine
def do_reconnect(conn, auto=True):
    if conn.connected:
        conn.quit("Reconnecting...")
        yield from asyncio.sleep(5)

    if auto:
        coro = conn.auto_reconnect()
    else:
        coro = conn.try_connect()

    try:
        yield from asyncio.wait_for(coro, 30)
    except asyncio.TimeoutError:
        return "Connection timed out"

    return "Reconnected to '{}'".format(conn.name)


@hook.command(autohelp=False, permissions=["botcontrol"], singlethread=True)
@asyncio.coroutine
def reconnect(conn, text, bot):
    """[connection] - Reconnects to [connection] or the current connection if not specified"""
    if not text:
        to_reconnect = conn
    else:
        try:
            to_reconnect = bot.connections[text.lower()]
        except KeyError:
            return "Connection '{}' not found".format(text)

    return (yield from do_reconnect(to_reconnect, False))


@hook.periodic(120, singlethread=True)
@asyncio.coroutine
def check_conns(bot):
    """
    :type bot: cloudbot.bot.CloudBot
    """
    for conn in bot.connections.values():
        if conn.active and not conn.connected:
            yield from do_reconnect(conn)


def format_conn(conn):
    lag = conn.memory["lag"]
    ping_interval = conn.config.get("ping_timeout", 60)
    if conn.connected:
        if lag > (ping_interval / 2):
            out = "$(yellow){name}$(clear) (lag: {activity} ms)"
        else:
            out = "$(green){name}$(clear) (lag: {activity} ms)"
    else:
        out = "$(red){name}$(clear)"

    return colors.parse(out.format(
        name=conn.name, activity=round(lag * 1000, 3)
    ))


@hook.command("connlist", "listconns", autohelp=False, permissions=["botcontrol"])
def list_conns(bot):
    """- Lists all current connections and their status"""
    conns = ', '.join(
        map(format_conn, bot.connections.values())
    )
    return "Current connections: {}".format(conns)


@hook.connect
def on_connect(conn):
    conn.memory["lag_sent"] = 0
    conn.memory["ping_recv"] = time.time()
    conn.memory["lag"] = 0


@hook.command("lagcheck", autohelp=False, permissions=["botcontrol"])
@hook.periodic(30)
@asyncio.coroutine
def lag_check(bot):
    now = time.time()
    for conn in bot.connections.values():
        if conn.connected:
            timeout = conn.config.get("ping_timeout", 60)
            lag = now - conn.memory.get("ping_recv", 0)

            if lag > timeout:
                yield from do_reconnect(conn)
            else:
                conn.send("PING :LAGCHECK{}".format(now))
                if not conn.memory["lag_sent"]:
                    conn.memory["lag_sent"] = now


@hook.irc_raw('PONG')
def on_pong(conn, irc_paramlist):
    now = time.time()
    conn.memory["ping_recv"] = now
    timestamp = irc_paramlist[-1].lstrip(':')
    is_lag = False
    if timestamp.startswith('LAGCHECK'):
        timestamp = timestamp[8:]
        is_lag = True

    t = float(timestamp)
    dif = now - t

    if is_lag:
        conn.memory["lag_sent"] = 0
        conn.memory["lag"] = dif
