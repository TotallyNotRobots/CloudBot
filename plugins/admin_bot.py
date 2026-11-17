from __future__ import annotations

import re
from typing import TYPE_CHECKING

from cloudbot import hook
from cloudbot.util import formatting

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot
    from cloudbot.client import Client
    from cloudbot.clients.irc import IrcClient
    from cloudbot.event import CommandEvent
    from cloudbot.event_functions import (
        EventAdminLog,
        EventIsNickValid,
        EventMessage,
        EventNotice,
        EventReply,
    )


@hook.command(
    "groups",
    "listgroups",
    "permgroups",
    permissions=["permissions_users"],
    autohelp=False,
)
def get_permission_groups(conn: Client) -> str:
    """- lists all valid groups"""
    return f"Valid groups: {[group.name for group in conn.permissions.get_groups()]}"


@hook.command("gperms", permissions=["permissions_users"])
def get_group_permissions(text, conn: Client, notice: EventNotice):
    """<group> - lists permissions given to <group>"""
    group = text.strip()
    permission_manager = conn.permissions
    if not permission_manager.group_exists(group):
        notice(f"Unknown group '{group}'")
        return None

    if group_permissions := permission_manager.get_group_permissions(group):
        return f"Group {group} has permissions {group_permissions}"

    return f"Group {group} exists, but has no permissions"


@hook.command("gusers", permissions=["permissions_users"])
def get_group_users(text, conn: Client, notice: EventNotice):
    """<group> - lists users in <group>"""
    group = text.strip()
    permission_manager = conn.permissions
    if not permission_manager.group_exists(group):
        notice(f"Unknown group '{group}'")
        return None

    if group_users := permission_manager.get_group_users(group):
        return f"Group {group} has members: {group_users}"

    return f"Group {group} exists, but has no members"


def parse_self(event):
    if event.text:
        if not event.has_permission("permissions_users"):
            event.notice(
                "Sorry, you are not allowed to use this command on another user"
            )
            return None

        return event.text.strip()

    return event.mask


@hook.command("uperms", autohelp=False)
def get_user_permissions(event):
    """[user] - lists all permissions given to [user], or the caller if no user is specified"""
    user = parse_self(event)
    if not user:
        return None

    permission_manager = event.conn.permissions

    if user_permissions := permission_manager.get_user_permissions(user):
        return f"User {user} has permissions: {user_permissions}"

    return f"User {user} has no elevated permissions"


@hook.command("ugroups", autohelp=False)
def get_user_groups(event):
    """[user] - lists all permissions given to [user], or the caller if no user is specified"""
    user = parse_self(event)
    if not user:
        return None

    permission_manager = event.conn.permissions

    if user_groups := permission_manager.get_user_groups(user):
        return (
            f"User {user} is in groups: {[group.name for group in user_groups]}"
        )

    return f"User {user} is in no permission groups"


def remove_user_from_group(user, group: str, event):
    permission_manager = event.conn.permissions
    changed_masks = permission_manager.remove_group_user(group, user)

    mask_list = formatting.get_text_list(changed_masks, "and")
    event.reply(f"Removed {mask_list} from {group}")
    event.admin_log(
        f"{event.nick} used deluser remove {mask_list} from {group}."
    )

    return bool(changed_masks)


@hook.command("deluser", permissions=["permissions_users"])
def remove_permission_user(text: str, event, conn: Client) -> None:
    """<user> [group] - removes <user> from [group], or from all groups if no group is specified"""
    split = text.split()
    if len(split) > 2:
        event.notice("Too many arguments")
        return

    if not split:
        event.notice("Not enough arguments")
        return

    perm_manager = conn.permissions
    user = split[0]
    if len(split) > 1:
        group = split[1]

        if group and not perm_manager.group_exists(group):
            event.notice(f"Unknown group '{group}'")
            return

        groups = [group] if perm_manager.user_in_group(user, group) else []
    else:
        groups = [g.name for g in perm_manager.get_user_groups(user)]

    if not groups:
        event.reply(f"No masks with elevated permissions matched {user}")
        return

    for group in groups:
        remove_user_from_group(user, group, event)


@hook.command("adduser", permissions=["permissions_users"])
def add_permissions_user(
    text: str,
    nick,
    conn: Client,
    notice: EventNotice,
    reply: EventReply,
    admin_log: EventAdminLog,
) -> None:
    """<user> <group> - adds <user> to <group>"""
    split = text.split()
    if len(split) > 2:
        notice("Too many arguments")
        return

    if len(split) < 2:
        notice("Not enough arguments")
        return

    user = split[0]
    group = split[1]

    if not re.search(".+!.+@.+", user):
        # TODO: When we have presence tracking, check if there are any users in the channel with the nick given
        notice("The user must be in the format 'nick!user@host'")
        return

    permission_manager = conn.permissions

    group_exists = permission_manager.group_exists(group)

    if not permission_manager.add_user_to_group(user, group):
        reply(f"User {user} is already matched in group {group}")
        return

    if group_exists:
        reply(f"User {user} added to group {group}")
        admin_log(f"{nick} used adduser to add {user} to {group}.")
    else:
        reply(f"Group {group} created with user {user}")
        admin_log(
            f"{nick} used adduser to create group {group} and add {user} to it."
        )


@hook.command("stopthebot", permissions=["botcontrol"])
async def stop(text, bot) -> None:
    """[reason] - stops me with [reason] as its quit message."""
    if text:
        await bot.stop(reason=text)
    else:
        await bot.stop()


@hook.command(permissions=["botcontrol"])
async def restart(text, bot) -> None:
    """[reason] - restarts me with [reason] as its quit message."""
    if text:
        await bot.restart(reason=text)
    else:
        await bot.restart()


@hook.command("rehash", "reload", permissions=["botcontrol"])
async def rehash_config(bot: CloudBot) -> str:
    """- Rehash config"""
    await bot.reload_config()
    return "Config reloaded."


@hook.command(permissions=["botcontrol", "snoonetstaff"])
def join(
    text: str,
    conn: Client,
    nick: str,
    notice: EventNotice,
    admin_log: EventAdminLog,
) -> None:
    """<channel> [key] - joins <channel> with the optional [key]"""
    parts = text.split(None, 1)
    target = parts.pop(0)

    if parts:
        key = parts.pop(0)
    else:
        key = None

    if not target.startswith("#"):
        target = f"#{target}"

    admin_log(f"{nick} used JOIN to make me join {target}.")
    notice(f"Attempting to join {target}...")
    conn.join(target, key)


def parse_targets(text, chan):
    if text:
        targets = text
    else:
        targets = chan

    return targets.split()


@hook.command(permissions=["botcontrol", "snoonetstaff"], autohelp=False)
def part(
    text,
    conn: Client,
    nick,
    chan,
    notice: EventNotice,
    admin_log: EventAdminLog,
) -> None:
    """[#channel] - parts [#channel], or the caller's channel if no channel is specified"""
    for target in parse_targets(text, chan):
        admin_log(f"{nick} used PART to make me leave {target}.")
        notice(f"Attempting to leave {target}...")
        conn.part(target)


@hook.command(autohelp=False, permissions=["botcontrol"])
def cycle(text, conn: Client, chan, notice: EventNotice) -> None:
    """[#channel] - cycles [#channel], or the caller's channel if no channel is specified"""
    for target in parse_targets(text, chan):
        notice(f"Attempting to cycle {target}...")
        conn.part(target)
        conn.join(target)


@hook.command("nick", permissions=["botcontrol"], clients=["irc"])
def change_nick(
    text, conn: IrcClient, notice: EventNotice, is_nick_valid: EventIsNickValid
) -> None:
    """<nick> - changes my nickname to <nick>"""
    if not is_nick_valid(text):
        notice(f"Invalid username '{text}'")
        return

    notice(f"Attempting to change nick to '{text}'...")
    conn.target_nick = text
    conn.set_nick(text)


@hook.command(permissions=["botcontrol"], clients=["irc"])
def raw(text, conn: IrcClient, notice: EventNotice) -> None:
    """<command> - sends <command> as a raw IRC command"""
    notice("Raw command sent.")
    conn.send(text)


def get_chan(chan, text):
    stripped_text = text.strip()
    if stripped_text.startswith("#") and " " in stripped_text:
        return tuple(stripped_text.split(None, 1))

    return chan, stripped_text


@hook.command(permissions=["botcontrol", "snoonetstaff"])
def say(text, conn: Client, chan, nick, admin_log: EventAdminLog) -> None:
    """[#channel] <message> - says <message> to [#channel], or to the caller's channel if no channel is specified"""
    channel, text = get_chan(chan, text)
    admin_log(f'{nick} used SAY to make me SAY "{text}" in {channel}.')
    conn.message(channel, text)


@hook.command("message", "sayto", permissions=["botcontrol", "snoonetstaff"])
def send_message(text, conn: Client, nick, admin_log: EventAdminLog) -> None:
    """<name> <message> - says <message> to <name>"""
    split = text.split(None, 1)
    channel = split[0]
    text = split[1]
    admin_log(f'{nick} used MESSAGE to make me SAY "{text}" in {channel}.')
    conn.message(channel, text)


@hook.command(
    "me", "act", clients=["irc"], permissions=["botcontrol", "snoonetstaff"]
)
def me(
    text: str, conn: IrcClient, chan: str, nick: str, event: CommandEvent
) -> None:
    """
    [#channel] <action> - acts out <action> in a [#channel], or in the current channel of none is specified
    """
    channel, text = get_chan(chan, text)
    event.admin_log(f'{nick} used ME to make me ACT "{text}" in {channel}.')
    conn.ctcp(channel, "ACTION", text)


@hook.command(autohelp=False, permissions=["botcontrol"])
def listchans(
    conn: Client, chan, message: EventMessage, notice: EventNotice
) -> None:
    """- Lists the current channels the bot is in"""
    chans = ", ".join(sorted(conn.channels, key=lambda x: x.strip("#").lower()))
    lines = formatting.chunk_str(f"I am currently in: {chans}")
    func = notice if chan[:1] == "#" else message
    for line in lines:
        func(line)
