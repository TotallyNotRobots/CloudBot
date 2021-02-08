"""
remind.py

Allows users to add reminders for various tasks.

Created By:
    - Pangea <https://github.com/PangeaCake>
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""

import time
from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy import Column, DateTime, PrimaryKeyConstraint, String, Table

from cloudbot import hook
from cloudbot.util import colors, database
from cloudbot.util.timeformat import format_time, time_since
from cloudbot.util.timeparse import time_parse

table = Table(
    "reminders",
    database.metadata,
    Column("network", String),
    Column("added_user", String),
    Column("added_time", DateTime),
    Column("added_chan", String),
    Column("message", String),
    Column("remind_time", DateTime),
    PrimaryKeyConstraint("network", "added_user", "added_time"),
)

ReminderCacheEntry = Tuple[str, datetime, datetime, str, str]

reminder_cache: List[ReminderCacheEntry] = []


async def delete_reminder(async_call, db, network, remind_time, user):
    query = (
        table.delete()
        .where(table.c.network == network.lower())
        .where(table.c.remind_time == remind_time)
        .where(table.c.added_user == user.lower())
    )
    await async_call(db.execute, query)
    await async_call(db.commit)


async def delete_all(async_call, db, network, user):
    query = (
        table.delete()
        .where(table.c.network == network.lower())
        .where(table.c.added_user == user.lower())
    )
    await async_call(db.execute, query)
    await async_call(db.commit)


async def add_reminder(
    async_call,
    db,
    network,
    added_user,
    added_chan,
    message,
    remind_time,
    added_time,
):
    query = table.insert().values(
        network=network.lower(),
        added_user=added_user.lower(),
        added_time=added_time,
        added_chan=added_chan.lower(),
        message=message,
        remind_time=remind_time,
    )
    await async_call(db.execute, query)
    await async_call(db.commit)


@hook.on_start()
async def load_cache(async_call, db):
    new_cache = []

    for network, remind_time, added_time, user, message in await async_call(
        _load_cache_db, db
    ):
        new_cache.append((network, remind_time, added_time, user, message))

    reminder_cache.clear()
    reminder_cache.extend(new_cache)


def _load_cache_db(db):
    query = db.execute(table.select())
    return [
        (
            row["network"],
            row["remind_time"],
            row["added_time"],
            row["added_user"],
            row["message"],
        )
        for row in query
    ]


@hook.periodic(30, initial_interval=30)
async def check_reminders(bot, async_call, db):
    current_time = datetime.now()

    for reminder in reminder_cache:
        network, remind_time, added_time, user, message = reminder
        if remind_time <= current_time:
            if network not in bot.connections:
                # connection is invalid
                continue

            conn = bot.connections[network]

            if not conn.ready:
                return

            remind_text = colors.parse(time_since(added_time, count=2))
            alert = colors.parse(
                "{}, you have a reminder from $(b){}$(clear) ago!".format(
                    user, remind_text
                )
            )

            conn.message(user, alert)
            conn.message(user, '"{}"'.format(message))

            delta = current_time - remind_time
            if delta > timedelta(minutes=30):
                late_time = time_since(remind_time, count=2)
                late = (
                    "(I'm sorry for delivering this message $(b){}$(clear) late,"
                    " it seems I was unable to deliver it on time)".format(
                        late_time
                    )
                )
                conn.message(user, colors.parse(late))

            await delete_reminder(async_call, db, network, remind_time, user)
            await load_cache(async_call, db)


@hook.command("remind", "reminder", "in")
async def remind(text, nick, chan, db, conn, event, async_call):
    """<1 minute, 30 seconds>: <do task> - reminds you to <do task> in <1 minute, 30 seconds>"""

    count = len(
        [
            x
            for x in reminder_cache
            if x[0] == conn.name and x[3] == nick.lower()
        ]
    )

    if text == "clear":
        if count == 0:
            return "You have no reminders to delete."

        await delete_all(async_call, db, conn.name, nick)
        await load_cache(async_call, db)
        return "Deleted all ({}) reminders for {}!".format(count, nick)

    # split the input on the first ":"
    parts = text.split(":", 1)

    if len(parts) == 1:
        # user didn't add a message, send them help
        event.notice_doc()
        return

    if count > 10:
        return (
            "Sorry, you already have too many reminders queued (10), you will need to wait or "
            "clear your reminders to add any more."
        )

    time_string = parts[0].strip()
    message = colors.strip_all(parts[1].strip())

    # get the current time in both DateTime and Unix Epoch
    current_epoch = time.time()
    current_time = datetime.fromtimestamp(current_epoch)

    # parse the time input, return error if invalid
    seconds = time_parse(time_string)
    if not seconds:
        return "Invalid input."

    if seconds > 2764800 or seconds < 60:
        return "Sorry, remind input must be more than a minute, and less than one month."

    # work out the time to remind the user, and check if that time is in the past
    remind_time = datetime.fromtimestamp(current_epoch + seconds)
    if remind_time < current_time:  # pragma: no cover
        # This should technically be unreachable because of the previous checks
        return "I can't remind you in the past!"

    # finally, add the reminder and send a confirmation message
    await add_reminder(
        async_call,
        db,
        conn.name,
        nick,
        chan,
        message,
        remind_time,
        current_time,
    )
    await load_cache(async_call, db)

    remind_text = format_time(seconds, count=2)
    output = 'Alright, I\'ll remind you "{}" in $(b){}$(clear)!'.format(
        message, remind_text
    )

    return colors.parse(output)
