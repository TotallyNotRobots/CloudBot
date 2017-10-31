"""
Bot wide hook opt-out for channels
"""
import asyncio
import copy
from collections import defaultdict
from fnmatch import fnmatch
from functools import total_ordering
from threading import RLock

from sqlalchemy import Table, Column, String, Boolean, PrimaryKeyConstraint, and_

from cloudbot import hook
from cloudbot.hook import Priority
from cloudbot.util import database, web

optout_table = Table(
    'optout',
    database.metadata,
    Column('network', String),
    Column('chan', String),
    Column('hook', String),
    Column('allow', Boolean, default=False),
    PrimaryKeyConstraint('network', 'chan', 'hook')
)

optout_cache = defaultdict(list)

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
        return "{}({}, {}, {})".format(self.__class__.__name__, self.channel, self.hook, self.allow)

    def match(self, channel, hook_name):
        return self.match_chan(channel) and fnmatch(hook_name.casefold(), self.hook)

    def match_chan(self, channel):
        return fnmatch(channel.casefold(), self.channel)


@hook.onload
def load_cache(db):
    with cache_lock:
        optout_cache.clear()
        for row in db.execute(optout_table.select()):
            optout_cache[row["network"]].append(OptOut(row["chan"], row["hook"], row["allow"]))

        for opts in optout_cache.values():
            opts.sort(reverse=True)


# noinspection PyUnusedLocal
@hook.sieve(priority=Priority.HIGHEST)
def optout_sieve(bot, event, _hook):
    if not event.chan or not event.conn:
        return event

    hook_name = _hook.plugin.title + "." + _hook.function_name
    with cache_lock:
        optouts = optout_cache[event.conn.name]
        for _optout in optouts:
            if _optout.match(event.chan, hook_name):
                if not _optout.allow:
                    if _hook.type == "command":
                        event.notice("Sorry, that command is disabled in this channel.")
                    return None
                return event

    return event


_STR_TO_BOOL = {
    "yes": True,
    "y": True,
    "no": False,
    "n": False,
    "on": True,
    "off": False,
    "enable": True,
    "disable": False,
    "allow": True,
    "deny": False,
}


def set_optout(db, conn, chan, pattern, allowed):
    conn_cf = conn.casefold()
    chan_cf = chan.casefold()
    pattern_cf = pattern.casefold()
    clause = and_(optout_table.c.network == conn_cf, optout_table.c.chan == chan_cf, optout_table.c.hook == pattern_cf)
    res = db.execute(optout_table.update().values(allow=allowed).where(clause))
    if not res.rowcount:
        db.execute(optout_table.insert().values(network=conn_cf, chan=chan_cf, hook=pattern_cf, allow=allowed))

    db.commit()
    load_cache(db)


def clear_optout(db, conn, chan=None):
    conn_cf = conn.casefold()
    if chan:
        chan_cf = chan.casefold()
        clause = and_(optout_table.c.network == conn_cf, optout_table.c.chan == chan_cf)
    else:
        clause = optout_table.c.network == conn_cf

    res = db.execute(optout_table.delete().where(clause))
    db.commit()
    load_cache(db)

    return res.rowcount


@asyncio.coroutine
@hook.command
def optout(text, event, db, conn):
    """[chan] <pattern> [allow] - Set the global allow option for hooks matching <pattern> in [chan], or the current channel if not specified
    :type text: str
    :type event: cloudbot.event.CommandEvent
    """
    args = text.split()
    old_chan = event.chan
    if args[0].startswith("#") and len(args) > 1:
        event.chan = args.pop(0)

    chan = event.chan

    has_perm = False
    for perm in ("chanop", "snoonetstaff", "botcontrol"):
        if (yield from event.check_permission(perm)):
            has_perm = True
            break

    event.chan = old_chan

    if not has_perm:
        event.notice("Sorry, you may not configure optout settings for that channel.")
        return

    pattern = args.pop(0)

    allowed = False
    if args:
        allow = args.pop(0)
        try:
            allowed = _STR_TO_BOOL[allow.lower()]
        except KeyError:
            return "Invalid allow option."

    yield from event.async_call(set_optout, db, conn.name, chan, pattern, allowed)

    return "{action} hooks matching {pattern} in {channel}.".format(
        action="Enabled" if allowed else "Disabled",
        pattern=pattern,
        channel=chan
    )


@hook.command("dumpoptout", permissions=["botcontrol", "snoonetstaff"], autohelp=False)
def dump_optout(conn):
    """- Dump the optout table to a pastebin"""
    with cache_lock:
        opts = copy.copy(optout_cache[conn.name])

    return web.paste(format_optout_list(opts), "markdown", "snoonet")


def get_channel_optouts(conn_name, chan):
    with cache_lock:
        return [opt for opt in optout_cache[conn_name] if opt.match_chan(chan)]


def gen_markdown_table(headers, rows):
    rows = copy.copy(rows)
    rows.insert(0, headers)
    rotated = zip(*reversed(rows))

    sizes = tuple(map(lambda l: max(map(len, l)), rotated))
    rows.insert(1, tuple(('-' * size) for size in sizes))
    lines = [
        "| {} |".format(' | '.join(cell.ljust(sizes[i]) for i, cell in enumerate(row)))
        for row in rows
    ]
    return '\n'.join(lines)


def format_optout_list(opts):
    headers = ("Channel Pattern", "Hook Pattern", "Allowed")
    table = [(opt.channel, opt.hook, "true" if opt.allow else "false") for opt in opts]
    return gen_markdown_table(headers, table)


@asyncio.coroutine
@hook.command("listoptout", autohelp=False)
def list_optout(conn, chan, text, event, async_call):
    """[channel] - View the global optout data for <channel> or the current channel if not specified
    :type conn: cloudbot.clients.irc.Client
    :type chan: str
    :type text: str
    :type event: cloudbot.event.Event
    """
    if text:
        chan = text.split()[0]

    old_chan = event.chan

    event.chan = chan
    allowed = False
    for perm in ("chanop", "op", "snoonetstaff", "botcontrol"):
        if (yield from event.check_permission(perm)):
            allowed = True
            break

    event.chan = old_chan

    if not allowed:
        event.notice("Sorry, you are not allowed to use this command.")
        return

    opts = yield from async_call(get_channel_optouts, conn.name, chan)
    table = yield from async_call(format_optout_list, opts)

    return web.paste(table, "markdown", "snoonet")


@asyncio.coroutine
@hook.command("clearoptout", autohelp=False)
def clear(conn, chan, text, event, db, async_call):
    """[channel] - Clears the optout list for a channel"""
    if text:
        chan = text.split()[0]

    old_chan = event.chan

    event.chan = chan
    allowed = False
    can_global = False
    for perm in ("snoonetstaff", "botcontrol"):
        if (yield from event.check_permission(perm)):
            allowed = True
            can_global = True
            break

    if not allowed:
        for perm in ("chanop", "op"):
            if (yield from event.check_permission(perm)):
                allowed = True
                break

    event.chan = old_chan

    if not allowed:
        event.notice("Sorry, you are not allowed to use this command.")
        return

    if chan.lower() == "global":
        if not can_global:
            event.notice("You do not have permission to clear global opt outs")
            return

        count = yield from async_call(clear_optout, db, conn.name)
    else:
        count = yield from async_call(clear_optout, db, conn.name, chan)

    return "Cleared {} opt outs from the list.".format(count)
