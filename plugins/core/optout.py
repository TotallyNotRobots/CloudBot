"""
Bot wide hook opt-out for channels
"""
import asyncio
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

    def match(self, channel, hook_name):
        return fnmatch(channel.casefold(), self.channel) and fnmatch(hook_name.casefold(), self.hook)


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


@hook.command("dumpoptout", permissions=["botcontrol"], autohelp=False)
def dump_optout(conn):
    """- Dump the optout table to a pastebin"""
    with cache_lock:
        out = '\n'.join(map(str, optout_cache[conn.name]))

    return web.paste(out)
