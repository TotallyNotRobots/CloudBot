import logging
from typing import Dict, Tuple

from sqlalchemy import Column, String, Table, UniqueConstraint

from cloudbot import hook
from cloudbot.util import database

table = Table(
    "regex_chans",
    database.metadata,
    Column("connection", String),
    Column("channel", String),
    Column("status", String),
    UniqueConstraint("connection", "channel"),
)

# Default value.
# If True, all channels without a setting will have regex enabled
# If False, all channels without a setting will have regex disabled
default_enabled = True
status_cache: Dict[Tuple[str, str], str] = {}
logger = logging.getLogger("cloudbot")


@hook.on_start()
def load_cache(db):
    new_cache = {}
    for row in db.execute(table.select()):
        conn = row["connection"]
        chan = row["channel"]
        status = row["status"]
        new_cache[(conn, chan)] = status

    status_cache.clear()
    status_cache.update(new_cache)


def set_status(db, conn, chan, status):
    if (conn, chan) in status_cache:
        # if we have a set value, update
        db.execute(
            table.update()
            .values(status=status)
            .where(table.c.connection == conn)
            .where(table.c.channel == chan)
        )
    else:
        # otherwise, insert
        db.execute(
            table.insert().values(connection=conn, channel=chan, status=status)
        )
    db.commit()


def delete_status(db, conn, chan):
    db.execute(
        table.delete()
        .where(table.c.connection == conn)
        .where(table.c.channel == chan)
    )
    db.commit()


@hook.sieve()
def sieve_regex(bot, event, _hook):
    if (
        _hook.type == "regex"
        and event.chan.startswith("#")
        and _hook.plugin.title != "factoids"
    ):
        status = status_cache.get((event.conn.name, event.chan))
        if status != "ENABLED" and (
            status == "DISABLED" or not default_enabled
        ):
            logger.info(
                "[%s] Denying %s from %s",
                event.conn.name,
                _hook.function_name,
                event.chan,
            )
            return None
        logger.info(
            "[%s] Allowing %s to %s",
            event.conn.name,
            _hook.function_name,
            event.chan,
        )

    return event


def change_status(db, event, status):
    text = event.text.strip().lower()
    if not text:
        channel = event.chan
    elif text.startswith("#"):
        channel = text
    else:
        channel = "#{}".format(text)

    action = "Enabling" if status else "Disabling"
    event.message(
        "{} regex matching (youtube, etc) (issued by {})".format(
            action, event.nick
        ),
        target=channel,
    )
    event.notice(
        "{} regex matching (youtube, etc) in channel {}".format(action, channel)
    )
    set_status(
        db, event.conn.name, channel, "ENABLED" if status else "DISABLED"
    )
    load_cache(db)


@hook.command(autohelp=False, permissions=["botcontrol"])
def enableregex(db, event):
    """[chan] - Enable regex hooks in [chan] (default: current channel)"""
    return change_status(db, event, True)


@hook.command(autohelp=False, permissions=["botcontrol"])
def disableregex(db, event):
    """[chan] - Disable regex hooks in [chan] (default: current channel)"""
    return change_status(db, event, False)


@hook.command(autohelp=False, permissions=["botcontrol"])
def resetregex(text, db, conn, chan, nick, message, notice):
    """[chan] - Reset regex hook status in [chan] (default: current channel)"""
    text = text.strip().lower()
    if not text:
        channel = chan
    elif text.startswith("#"):
        channel = text
    else:
        channel = "#{}".format(text)

    message(
        "Resetting regex matching setting (youtube, etc) (issued by {})".format(
            nick
        ),
        target=channel,
    )
    notice(
        "Resetting regex matching setting (youtube, etc) in channel {}".format(
            channel
        )
    )
    delete_status(db, conn.name, channel)
    load_cache(db)


@hook.command(autohelp=False, permissions=["botcontrol"])
def regexstatus(text, conn, chan):
    """[chan] - Get status of regex hooks in [chan] (default: current channel)"""
    text = text.strip().lower()
    if not text:
        channel = chan
    elif text.startswith("#"):
        channel = text
    else:
        channel = "#{}".format(text)
    status = status_cache.get((conn.name, chan))
    if status is None:
        if default_enabled:
            status = "ENABLED"
        else:
            status = "DISABLED"
    return "Regex status for {}: {}".format(channel, status)


@hook.command(autohelp=False, permissions=["botcontrol"])
def listregex(conn):
    """- List non-default regex statuses for channels"""
    values = []
    for (conn_name, chan), status in status_cache.items():
        if conn_name != conn.name:
            continue
        values.append("{}: {}".format(chan, status))
    return ", ".join(values)
