import logging
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from sqlalchemy import Column, String, Table, UniqueConstraint

from cloudbot import hook
from cloudbot.util import database

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot
    from cloudbot.client import Client
    from cloudbot.event import Event
    from cloudbot.plugin_hooks import Hook

table = Table(
    "regex_chans",
    database.metadata,
    Column("connection", String),
    Column("channel", String),
    Column("status", String),
    UniqueConstraint("connection", "channel"),
)

ENABLED = "ENABLED"
DISABLED = "DISABLED"

# Default value.
# If True, all channels without a setting will have regex enabled
# If False, all channels without a setting will have regex disabled
default_enabled = True
status_cache: Dict[Tuple[str, str], bool] = {}
logger = logging.getLogger("cloudbot")


@hook.on_start()
def load_cache(db):
    new_cache = {}
    for row in db.execute(table.select()):
        conn = row["connection"]
        chan = row["channel"]
        status = row["status"]
        if status == ENABLED:
            value = True
        elif status == DISABLED:
            value = False
        else:
            # Unknown values just use the default (existing behavior)
            logger.warning(
                "[regex_chans] Unknown status: %s, falling back to default",
                tuple(row),
            )
            continue

        new_cache[(conn, chan)] = value

    status_cache.clear()
    status_cache.update(new_cache)


def set_status(db, conn, chan, status: bool):
    status_value = ENABLED if status else DISABLED
    if (conn, chan) in status_cache:
        # if we have a set value, update
        db.execute(
            table.update()
            .values(status=status_value)
            .where(table.c.connection == conn)
            .where(table.c.channel == chan)
        )
    else:
        # otherwise, insert
        db.execute(
            table.insert().values(
                connection=conn, channel=chan, status=status_value
            )
        )

    db.commit()
    load_cache(db)


def delete_status(db, conn, chan):
    db.execute(
        table.delete()
        .where(table.c.connection == conn)
        .where(table.c.channel == chan)
    )

    db.commit()
    load_cache(db)


def get_status(conn: "Client", chan: str) -> bool:
    return status_cache.get((conn.name, chan), default_enabled)


def parse_args(text: str, chan: str) -> str:
    text = text.strip().lower()
    if not text:
        channel = chan
    elif text.startswith("#"):
        channel = text
    else:
        channel = f"#{text}"

    return channel


def change_status(db, event, status):
    channel = parse_args(event.text, event.chan)
    action = "Enabling" if status else "Disabling"
    event.message(
        "{} regex matching (youtube, etc) (issued by {})".format(
            action, event.nick
        ),
        target=channel,
    )

    event.notice(f"{action} regex matching (youtube, etc) in channel {channel}")
    set_status(db, event.conn.name, channel, status)


@hook.sieve()
def sieve_regex(
    bot: "CloudBot", event: "Event", _hook: "Hook"
) -> Optional["Event"]:
    if (
        _hook.type == "regex"
        and event.chan.startswith("#")
        and _hook.plugin.title != "factoids"
    ):
        if not get_status(event.conn, event.chan):
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
    channel = parse_args(text, chan)
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


@hook.command(autohelp=False, permissions=["botcontrol"])
def regexstatus(text: str, conn: "Client", chan: str) -> str:
    """[chan] - Get status of regex hooks in [chan] (default: current channel)"""
    channel = parse_args(text, chan)
    status = get_status(conn, channel)
    return f"Regex status for {channel}: {ENABLED if status else DISABLED}"


@hook.command(autohelp=False, permissions=["botcontrol"])
def listregex(conn: "Client") -> str:
    """- List non-default regex statuses for channels"""
    values = []
    for (conn_name, chan), status in status_cache.items():
        if conn_name != conn.name:
            continue

        values.append(f"{chan}: {ENABLED if status else DISABLED}")

    return ", ".join(values)
