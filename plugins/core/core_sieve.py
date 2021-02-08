import logging
from time import time
from typing import Dict, Optional

from cloudbot import hook
from cloudbot.bot import CloudBot
from cloudbot.event import CommandEvent, Event
from cloudbot.plugin_hooks import Hook
from cloudbot.util.tokenbucket import TokenBucket

ready = False
buckets: Dict[str, TokenBucket] = {}
logger = logging.getLogger("cloudbot")


@hook.periodic(600)
def task_clear():
    for uid, _bucket in buckets.copy().items():
        if (time() - _bucket.timestamp) > 600:
            del buckets[uid]


# noinspection PyUnusedLocal
@hook.sieve()
def check_acls(bot: CloudBot, event: Event, _hook: Hook) -> Optional[Event]:
    """
    Handle config ACLs
    """
    if event.chan is None:
        return event

    conn = event.conn

    # check acls
    acl = conn.config.get("acls", {}).get(_hook.function_name, {})
    allowlist = acl.get("deny-except")
    denylist = acl.get("allow-except")

    chan = event.chan.lower()
    if allowlist is not None:
        allowed_channels = list(map(str.lower, allowlist))
        if chan not in allowed_channels:
            return None

    if denylist is not None:
        denied_channels = list(map(str.lower, denylist))
        if chan in denied_channels:
            return None

    return event


# noinspection PyUnusedLocal
@hook.sieve()
async def perm_sieve(
    bot: CloudBot, event: Event, _hook: Hook
) -> Optional[Event]:
    """check permissions"""
    allowed_permissions = _hook.permissions
    if allowed_permissions:
        allowed = False
        for perm in allowed_permissions:
            if await event.check_permission(perm):
                allowed = True
                break

        if not allowed:
            event.notice("Sorry, you are not allowed to use this command.")
            return None

    return event


# noinspection PyUnusedLocal
@hook.sieve()
def check_disabled(
    bot: CloudBot, event: CommandEvent, _hook: Hook
) -> Optional[Event]:
    """
    check disabled_commands
    """
    conn = event.conn
    if _hook.type == "command":
        disabled_commands = conn.config.get("disabled_commands", [])
        if event.triggered_command in disabled_commands:
            return None

    return event


# noinspection PyUnusedLocal
@hook.sieve()
def rate_limit(bot: CloudBot, event: Event, _hook: Hook) -> Optional[Event]:
    """
    Handle rate limiting certain hooks
    """
    conn = event.conn
    # check command spam tokens
    if _hook.type in ("command", "regex"):
        uid = "!".join([conn.name, event.chan, event.nick]).lower()

        config = conn.config.get("ratelimit", {})
        tokens = config.get("tokens", 17.5)
        restore_rate = config.get("restore_rate", 2.5)
        message_cost = config.get("message_cost", 5)
        strict = config.get("strict", True)

        try:
            bucket = buckets[uid]
        except KeyError:
            buckets[uid] = bucket = TokenBucket(tokens, restore_rate)

        if not bucket.consume(message_cost):
            logger.info(
                "[%s|sieve] Refused command from %s. Entity had %s tokens, needed %s.",
                conn.name,
                uid,
                bucket.tokens,
                message_cost,
            )
            if strict:
                # bad person loses all tokens
                bucket.empty()

            return None

    return event
