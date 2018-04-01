from sqlalchemy import Table, Column, UniqueConstraint, String

from cloudbot import hook
from cloudbot.util import database

table = Table(
    "regex_chans",
    database.metadata,
    Column("connection", String),
    Column("channel", String),
    Column("status", String),
    UniqueConstraint("connection", "channel")
)

# Default value.
# If True, all channels without a setting will have regex enabled
# If False, all channels without a setting will have regex disabled
default_enabled = True


@hook.on_start()
def load_cache(event):
    global status_cache
    status_cache = {}
    with event.db_session() as db:
        rows = db.execute(table.select()).fetchall()

    for row in rows:
        conn = row["connection"]
        chan = row["channel"]
        status = row["status"]
        status_cache[(conn, chan)] = status


def set_status(event, conn, chan, status):
    """
    :type event: cloudbot.event.Event
    :type conn: str
    :type chan: str
    :type status: str
    """
    conn = conn.lower()
    chan = chan.lower()

    with event.db_session() as db:
        if (conn, chan) in status_cache:
            # if we have a set value, update
            db.execute(
                table.update().values(status=status).where(table.c.connection == conn).where(table.c.channel == chan))
        else:
            # otherwise, insert
            db.execute(table.insert().values(connection=conn, channel=chan, status=status))
        db.commit()


def delete_status(event, conn, chan):
    conn = conn.lower()
    chan = chan.lower()

    with event.db_session() as db:
        db.execute(table.delete().where(table.c.connection == conn).where(table.c.channel == chan))
        db.commit()


@hook.sieve()
def sieve_regex(event, bot):
    _hook = event.hook
    if _hook.type == "regex" and event.chan is not None and event.is_channel(event.chan) and _hook.plugin.title != "factoids":
        status = status_cache.get((event.conn.name, event.chan))
        if status != "ENABLED" and (status == "DISABLED" or not default_enabled):
            bot.logger.info("[{}] Denying {} from {}".format(event.conn.name, _hook.function_name, event.chan))
            return None
        bot.logger.info("[{}] Allowing {} to {}".format(event.conn.name, _hook.function_name, event.chan))

    return event


def get_channel(event):
    """
    :type event: cloudbot.event.CommandEvent
    :rtype: str
    """
    text = event.text
    chan = event.chan
    text = text.strip()
    if text:
        if not event.is_channel(text):
            event.notice("Invalid channel {!r}".format(text))
            return None

        channel = text
    else:
        channel = chan

    return channel


@hook.command(autohelp=False, permissions=["botcontrol"])
def enableregex(conn, nick, message, notice, event):
    channel = get_channel(event)
    if channel is None:
        return

    message("Enabling regex matching (youtube, etc) (issued by {})".format(nick), target=channel)
    notice("Enabling regex matching (youtube, etc) in channel {}".format(channel))
    set_status(event, conn.name, channel, "ENABLED")
    load_cache(event)


@hook.command(autohelp=False, permissions=["botcontrol"])
def disableregex(conn, event, nick, message, notice):
    channel = get_channel(event)
    if channel is None:
        return

    message("Disabling regex matching (youtube, etc) (issued by {})".format(nick), target=channel)
    notice("Disabling regex matching (youtube, etc) in channel {}".format(channel))
    set_status(event, conn.name, channel, "DISABLED")
    load_cache(event)


@hook.command(autohelp=False, permissions=["botcontrol"])
def resetregex(conn, event, nick, message, notice):
    channel = get_channel(event)
    if channel is None:
        return

    message("Resetting regex matching setting (youtube, etc) (issued by {})".format(nick), target=channel)
    notice("Resetting regex matching setting (youtube, etc) in channel {}".format(channel))
    delete_status(event, conn.name, channel)
    load_cache(event)


@hook.command(autohelp=False, permissions=["botcontrol"])
def regexstatus(conn, chan, event):
    channel = get_channel(event)
    if channel is None:
        return

    status = status_cache.get((conn.name, chan))
    if status is None:
        if default_enabled:
            status = "ENABLED"
        else:
            status = "DISABLED"

    return "Regex status for {}: {}".format(channel, status)


@hook.command(autohelp=False, permissions=["botcontrol"])
def listregex(conn):
    values = []
    for (conn_name, chan), status in status_cache.values():
        if conn_name != conn.name:
            continue

        values.append("{}: {}".format(chan, status))

    return ", ".join(values)
