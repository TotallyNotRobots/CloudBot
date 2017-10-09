import asyncio

from cloudbot import hook
from cloudbot.util import colors


@hook.command(autohelp=False, permissions=["botcontrol"])
def conncheck(nick, bot, notice):
    """This command is an effort to make the bot reconnect to a network if it has been disconnected."""
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
    if conn.connected:
        out = "$(green){name}$(clear)"
    else:
        out = "$(red){name}$(clear)"

    return colors.parse(out.format(name=conn.name))


@hook.command("connlist", "listconns", autohelp=False, permissions=["botcontrol"])
def list_conns(bot):
    """- Lists all current connections and their status"""
    conns = ', '.join(
        map(format_conn, bot.connections.values())
    )
    return "Current connections: {}".format(conns)
