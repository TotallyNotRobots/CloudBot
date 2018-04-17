import asyncio

from cloudbot import hook
from cloudbot.util import formatting


@hook.command("stop", "stopthebot", "shutdown", permissions=["botcontrol"], autohelp=False)
@asyncio.coroutine
def stop(text, bot):
    """[reason] - stops me with [reason] as its quit message.
    :type text: str
    :type bot: cloudbot.bot.CloudBot
    """
    if text:
        yield from bot.stop(reason=text)
    else:
        yield from bot.stop()


@hook.command("reload", "reloadconfig", permissions=["botcontrol"], autohelp=False)
def reload(bot, notice):
    notice("Reloading config...")
    bot.reload_config()
    notice("Config reloaded.")


@hook.command(permissions=["botcontrol"], autohelp=False)
@asyncio.coroutine
def restart(text, bot):
    """[reason] - restarts me with [reason] as its quit message.
    :type text: str
    :type bot: cloudbot.bot.CloudBot
    """
    if text:
        yield from bot.restart(reason=text)
    else:
        yield from bot.restart()


@hook.command(permissions=["botcontrol", "snoonetstaff"])
@asyncio.coroutine
def join(text, conn, nick, notice, admin_log, event):
    """<channel> - joins <channel>
    :type text: str
    :type conn: cloudbot.client.Client
    :type event: cloudbot.event.Event
    """
    if not event.is_channel(text):
        return "That channel name is not valid."

    admin_log("{} used JOIN to make me join {}.".format(nick, text))
    notice("Attempting to join {}...".format(text))
    conn.join(text)


@hook.command(permissions=["botcontrol", "snoonetstaff"], autohelp=False)
@asyncio.coroutine
def part(text, conn, nick, chan, event):
    """[#channel] - parts [#channel], or the caller's channel if no channel is specified
    :type text: str
    :type conn: cloudbot.client.Client
    :type nick: str
    :type chan: str
    :type event: cloudbot.event.Event
    """
    if text:
        if not event.is_channel(text):
            return "That channel name is not valid."

        target = text
    else:
        target = chan

    event.admin_log("{} used PART to make me leave {}.".format(nick, target))
    event.notice("Attempting to leave {}...".format(target))
    conn.part(target)


@hook.command(autohelp=False, permissions=["botcontrol"])
@asyncio.coroutine
def cycle(text, conn, chan, notice, event):
    """[#channel] - cycles [#channel], or the caller's channel if no channel is specified
    :type text: str
    :type conn: cloudbot.client.Client
    :type chan: str
    """
    if text:
        if not event.is_channel(text):
            return "That channel name is not valid."

        target = text
    else:
        target = chan

    notice("Attempting to cycle {}...".format(target))
    conn.part(target)
    conn.join(target)


@hook.command("nick", permissions=["botcontrol"])
@asyncio.coroutine
def change_nick(text, conn, notice, is_nick_valid):
    """<nick> - changes my nickname to <nick>
    :type text: str
    :type conn: cloudbot.client.Client
    """
    if not is_nick_valid(text):
        notice("Invalid username '{}'".format(text))
        return

    notice("Attempting to change nick to '{}'...".format(text))
    conn.set_nick(text)


@hook.command(permissions=["botcontrol"])
@asyncio.coroutine
def raw(text, conn, notice):
    """<command> - sends <command> as a raw IRC command
    :type text: str
    :type conn: cloudbot.client.Client
    """
    notice("Raw command sent.")
    conn.send(text)


@hook.command(permissions=["botcontrol", "snoonetstaff"])
@asyncio.coroutine
def say(text, conn, chan, nick, admin_log, event):
    """[#channel] <message> - says <message> to [#channel], or to the caller's channel if no channel is specified
    :type text: str
    :type conn: cloudbot.client.Client
    :type chan: str
    :type event: cloudbot.event.Evemt
    """
    split = text.split(None, 1)
    if event.is_channel(split[0]) and len(split) > 1:
        channel = split[0]
        text = split[1]
    else:
        channel = chan

    admin_log("{} used SAY to make me SAY \"{}\" in {}.".format(nick, text, channel))
    conn.message(channel, text)


@hook.command("message", "sayto", permissions=["botcontrol", "snoonetstaff"])
@asyncio.coroutine
def say_message(text, conn, nick, admin_log):
    """<name> <message> - says <message> to <name>
    :type text: str
    :type conn: cloudbot.client.Client
    """
    split = text.split(None, 1)
    channel = split[0]
    text = split[1]
    admin_log("{} used MESSAGE to make me SAY \"{}\" in {}.".format(nick, text, channel))
    conn.message(channel, text)


@hook.command("me", "act", permissions=["botcontrol", "snoonetstaff"])
@asyncio.coroutine
def me(text, conn, chan, nick, admin_log, event):
    """[#channel] <action> - acts out <action> in a [#channel], or in the current channel of none is specified
    :type text: str
    :type conn: cloudbot.client.Client
    :type chan: str
    :type event: cloudbot.event.Event
    """
    split = text.split(None, 1)
    if event.is_channel(split[0]) and len(split) > 1:
        channel = split[0]
        text = split[1]
    else:
        channel = chan

    admin_log("{} used ME to make me ACT \"{}\" in {}.".format(nick, text, channel))
    conn.action(channel, text)


@hook.command(autohelp=False, permissions=["botcontrol"])
@asyncio.coroutine
def listchans(conn, chan, message, notice, nick):
    """- Lists the current channels the bot is in"""
    chans = ', '.join(sorted(conn.channels))
    lines = formatting.chunk_str("I am currently in: {}".format(chans))
    for line in lines:
        if chan == nick:
            message(line)
        else:
            notice(line)
