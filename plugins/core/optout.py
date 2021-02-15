"""
Bot wide hook opt-out for channels
"""
from collections import defaultdict
from functools import total_ordering
from threading import RLock

from irclib.util.compare import match_mask
from sqlalchemy import (
    Boolean,
    Column,
    PrimaryKeyConstraint,
    String,
    Table,
    and_,
)

from cloudbot import hook
from cloudbot.hook import Priority
from cloudbot.util import database, web
from cloudbot.util.formatting import gen_markdown_table
from cloudbot.util.mapping import DefaultKeyFoldDict
from cloudbot.util.text import parse_bool

optout_table = Table(
    "optout",
    database.metadata,
    Column("network", String),
    Column("chan", String),
    Column("hook", String),
    Column("allow", Boolean, default=False),
    PrimaryKeyConstraint("network", "chan", "hook"),
)

optout_cache = DefaultKeyFoldDict(list)

cache_lock = RLock()


@total_ordering
class OptOut:
    def __init__(self, channel, hook_pattern, allow):
        self.channel = channel.casefold()
        self.hook = hook_pattern.casefold()
        self.allow = allow

    def __lt__(self, other):
        if isinstance(other, OptOut):
            diff = len(self.channel) - len(other.channel)
            if diff:
                return diff < 0

            return len(self.hook) < len(other.hook)

        return NotImplemented

    def __str__(self):
        return "{} {} {}".format(self.channel, self.hook, self.allow)

    def __repr__(self):
        return "{}({}, {}, {})".format(
            self.__class__.__name__, self.channel, self.hook, self.allow
        )

    def match(self, channel, hook_name):
        return self.match_chan(channel) and match_mask(
            hook_name.casefold(), self.hook
        )

    def match_chan(self, channel):
        return match_mask(channel.casefold(), self.channel)


async def check_channel_permissions(event, chan, *perms):
    old_chan = event.chan
    event.chan = chan

    allowed = await event.check_permissions(*perms)

    event.chan = old_chan
    return allowed


def get_conn_optouts(conn_name):
    with cache_lock:
        return optout_cache[conn_name.casefold()]


def get_channel_optouts(conn_name, chan=None):
    with cache_lock:
        return [
            opt
            for opt in get_conn_optouts(conn_name)
            if not chan or opt.match_chan(chan)
        ]


def format_optout_list(opts):
    headers = ("Channel Pattern", "Hook Pattern", "Allowed")
    table = [
        (opt.channel, opt.hook, "true" if opt.allow else "false")
        for opt in opts
    ]
    return gen_markdown_table(headers, table)


def set_optout(db, conn, chan, pattern, allowed):
    conn_cf = conn.casefold()
    chan_cf = chan.casefold()
    pattern_cf = pattern.casefold()
    clause = and_(
        optout_table.c.network == conn_cf,
        optout_table.c.chan == chan_cf,
        optout_table.c.hook == pattern_cf,
    )
    res = db.execute(optout_table.update().values(allow=allowed).where(clause))
    if not res.rowcount:
        db.execute(
            optout_table.insert().values(
                network=conn_cf, chan=chan_cf, hook=pattern_cf, allow=allowed
            )
        )

    db.commit()
    load_cache(db)


def del_optout(db, conn, chan, pattern):
    conn_cf = conn.casefold()
    chan_cf = chan.casefold()
    pattern_cf = pattern.casefold()
    clause = and_(
        optout_table.c.network == conn_cf,
        optout_table.c.chan == chan_cf,
        optout_table.c.hook == pattern_cf,
    )
    res = db.execute(optout_table.delete().where(clause))

    db.commit()
    load_cache(db)

    return res.rowcount > 0


def clear_optout(db, conn, chan=None):
    conn_cf = conn.casefold()
    if chan:
        chan_cf = chan.casefold()
        clause = and_(
            optout_table.c.network == conn_cf, optout_table.c.chan == chan_cf
        )
    else:
        clause = optout_table.c.network == conn_cf

    res = db.execute(optout_table.delete().where(clause))
    db.commit()
    load_cache(db)

    return res.rowcount


@hook.onload()
def load_cache(db):
    new_cache = defaultdict(list)
    for row in db.execute(optout_table.select()):
        new_cache[row["network"]].append(
            OptOut(row["chan"], row["hook"], row["allow"])
        )

    for opts in new_cache.values():
        opts.sort(reverse=True)

    with cache_lock:
        optout_cache.clear()
        optout_cache.update(new_cache)


# noinspection PyUnusedLocal
@hook.sieve(priority=Priority.HIGHEST)
def optout_sieve(bot, event, _hook):
    if not event.chan or not event.conn:
        return event

    if _hook.plugin.title.startswith("core."):
        return event

    hook_name = _hook.plugin.title + "." + _hook.function_name
    with cache_lock:
        optouts = get_conn_optouts(event.conn.name)
        for _optout in optouts:
            if _optout.match(event.chan, hook_name):
                if not _optout.allow:
                    if _hook.type == "command":
                        event.notice(
                            "Sorry, that command is disabled in this channel."
                        )

                    return None

                break

    return event


@hook.command()
async def optout(text, event, chan, db, conn):
    """[chan] <pattern> [allow] - Set the global allow option for hooks matching <pattern> in [chan], or the current
    channel if not specified
    """
    args = text.split()
    if args[0].startswith("#") and len(args) > 1:
        chan = args.pop(0)

    has_perm = await check_channel_permissions(
        event, chan, "op", "chanop", "snoonetstaff", "botcontrol"
    )

    if not has_perm:
        event.notice(
            "Sorry, you may not configure optout settings for that channel."
        )
        return

    pattern = args.pop(0)

    allowed = False
    if args:
        allow = args.pop(0)
        try:
            allowed = parse_bool(allow)
        except KeyError:
            return "Invalid allow option."

    await event.async_call(set_optout, db, conn.name, chan, pattern, allowed)

    return "{action} hooks matching {pattern} in {channel}.".format(
        action="Enabled" if allowed else "Disabled",
        pattern=pattern,
        channel=chan,
    )


@hook.command()
async def deloptout(text, event, chan, db, conn):
    """[chan] <pattern> - Delete global optout hooks matching <pattern> in [chan], or the current channel if not
    specified"""
    args = text.split()
    if len(args) > 1:
        chan = args.pop(0)

    has_perm = await check_channel_permissions(
        event, chan, "op", "chanop", "snoonetstaff", "botcontrol"
    )

    if not has_perm:
        event.notice(
            "Sorry, you may not configure optout settings for that channel."
        )
        return

    pattern = args.pop(0)

    deleted = await event.async_call(del_optout, db, conn.name, chan, pattern)

    if deleted:
        return "Deleted optout '{}' in channel '{}'.".format(pattern, chan)

    return "No matching optouts in channel '{}'.".format(chan)


async def check_global_perms(event):
    chan = event.chan
    text = event.text
    if text:
        chan = text.split()[0]

    can_global = await event.check_permissions("snoonetstaff", "botcontrol")
    allowed = can_global or (
        await check_channel_permissions(event, chan, "op", "chanop")
    )

    if not allowed:
        event.notice("Sorry, you are not allowed to use this command.")

    if chan.lower() == "global":
        if not can_global:
            event.notice("You do not have permission to access global opt outs")
            allowed = False

        chan = None

    return chan, allowed


@hook.command("listoptout", autohelp=False)
async def list_optout(conn, event, async_call):
    """[channel] - View the opt out data for <channel> or the current channel if not specified. Specify "global" to
    view all data for this network
    """
    chan, allowed = await check_global_perms(event)

    if not allowed:
        return

    opts = await async_call(get_channel_optouts, conn.name, chan)
    table = await async_call(format_optout_list, opts)

    return await async_call(web.paste, table, "md", "hastebin")


@hook.command("clearoptout", autohelp=False)
async def clear(conn, event, db, async_call):
    """[channel] - Clears the optout list for a channel. Specify "global" to clear all data for this network"""
    chan, allowed = await check_global_perms(event)

    if not allowed:
        return

    count = await async_call(clear_optout, db, conn.name, chan)

    return "Cleared {} opt outs from the list.".format(count)
