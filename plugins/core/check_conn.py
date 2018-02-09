import asyncio
import time

from cloudbot import hook
from cloudbot.util import colors


@asyncio.coroutine
def do_reconnect(conn, auto=True):
    if conn.connected:
        conn.quit("Reconnecting...")
        yield from asyncio.sleep(5)

    if auto:
        coro = conn.auto_reconnect()
    else:
        coro = conn.connect(30)

    try:
        yield from coro
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
    try:
        warning = conn.config["ping_settings"]["warn"]
    except LookupError:
        warning = 120

    if conn.connected:
        if lag >= warning:
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
    now = time.time()
    conn.memory["lag_sent"] = 0
    conn.memory["ping_recv"] = now
    conn.memory["last_activity"] = now
    conn.memory["lag"] = 0
    conn.memory["needs_reconnect"] = False


@hook.command("lagcheck", autohelp=False, permissions=["botcontrol"])
@hook.periodic(5)
def lag_check(bot, admin_log):
    now = time.time()
    for conn in bot.connections.values():
        if conn.connected:
            ping_conf = conn.config.get("ping_settings", {})
            interval = ping_conf.get("interval", 60)
            warning = ping_conf.get("warn", 120)
            timeout = ping_conf.get("timeout", 300)

            last_ping = conn.memory.get("last_ping_rpl", 0)
            if conn.memory["lag_sent"]:
                last_ping = conn.memory["lag_sent"]

            ping_diff = now - last_ping
            lag = conn.memory.get("lag", 0)
            last_act = now - conn.memory.get("last_activity", 0)
            if lag > warning or last_act > warning:
                admin_log(
                    "[{}] Lag detected. {:.2f}s since last ping, {:.2f}s since last activity".format(
                        conn.name, lag, last_act
                    )
                )

            if lag > timeout and last_act > timeout:
                conn.memory["needs_reconnect"] = True
            elif ping_diff >= interval:
                conn.send("PING :LAGCHECK{}".format(now))
                if not conn.memory["lag_sent"]:
                    conn.memory["lag_sent"] = now


@hook.periodic(30, singlethread=True)
@asyncio.coroutine
def reconnect_loop(bot):
    for conn in bot.connections.values():
        if conn.memory.get("needs_reconnect"):
            yield from do_reconnect(conn)


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
        conn.memory["last_ping_rpl"] = now


@hook.irc_raw('*')
@asyncio.coroutine
def on_act(conn):
    now = time.time()
    conn.memory['last_activity'] = now
