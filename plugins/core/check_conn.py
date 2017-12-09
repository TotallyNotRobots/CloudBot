import asyncio
import time
from functools import partial

from cloudbot import hook
from cloudbot.util import colors, async_util


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
            bot.connections[conn].connect()
        # Send a message from each irc network connection to the nick that issued the command
        bot.connections[conn].message(nick, "just letting you know I am here. {}".format(conn))


@asyncio.coroutine
@hook.command(autohelp=False, permissions=["botcontrol"], singlethread=True)
def reconnect(conn, text, bot):
    """[connection] - Reconnects to [connection] or the current connection if not specified"""
    if not text:
        to_reconnect = conn
    else:
        try:
            to_reconnect = bot.connections[text.lower()]
        except KeyError:
            return "Connection '{}' not found".format(text)

    if to_reconnect.connected:
        to_reconnect.quit("Reconnecting...")
        yield from asyncio.sleep(1)
        to_reconnect._quit = False

    coro = to_reconnect.connect()
    try:
        yield from asyncio.wait_for(coro, 30)
    except asyncio.TimeoutError:
        return "Connection timed out"
    except Exception as e:
        return "{}: {}".format(type(e).__name__, e)

    return "Reconnected to '{}'".format(conn.name)


def format_conn(conn):
    act_time = time.time() - conn.memory.get("last_activity", 0)
    ping_interval = conn.config.get("ping_interval", 60)
    if conn.connected:
        if act_time > ping_interval:
            out = "$(yellow){name}$(clear) (last activity: {activity} secs)"
        else:
            out = "$(green){name}$(clear)"
    else:
        out = "$(red){name}$(clear)"

    return colors.parse(out.format(
        name=conn.name, activity=round(act_time, 3)
    ))


@hook.command("connlist", "listconns", autohelp=False, permissions=["botcontrol"])
def list_conns(bot):
    """- Lists all current connections and their status"""
    conns = ', '.join(
        map(format_conn, bot.connections.values())
    )
    return "Current connections: {}".format(conns)


@hook.periodic(5)
def pinger(bot):
    for conn in bot.connections.values():
        if conn.connected:
            ping_interval = conn.config.get("ping_interval", 60)
            # This is updated by a catch-all hook, so any activity from the server will indicate a live connection
            # This mimics most modern clients, as they will only send a ping if they have not received any data recently
            last_act = conn.memory.get("last_activity")
            # If the activity time isn't set, default to the current time.
            # This avoids an issue where the bot would reconnect just after loading this plugin
            if last_act is None:
                conn.memory["last_activity"] = time.time()
                continue

            diff = time.time() - last_act
            if diff >= (ping_interval * 2):
                conn.quit("Reconnecting due to lag...")
                time.sleep(1)
                conn._quit = False
                conn.loop.call_soon_threadsafe(
                    partial(async_util.wrap_future, conn.connect(), loop=conn.loop)
                )
            elif diff >= ping_interval:
                conn.send("PING :LAGCHECK{}".format(time.time()))


@hook.irc_raw('*')
def on_activity(conn):
    conn.memory["last_activity"] = time.time()
