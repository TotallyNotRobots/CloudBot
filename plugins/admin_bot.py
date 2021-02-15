import re

from cloudbot import hook
from cloudbot.bot import CloudBot
from cloudbot.clients.irc import IrcClient
from cloudbot.event import CommandEvent
from cloudbot.util import formatting


@hook.command(
    "groups",
    "listgroups",
    "permgroups",
    permissions=["permissions_users"],
    autohelp=False,
)
async def get_permission_groups(conn):
    """- lists all valid groups"""
    return "Valid groups: {}".format(conn.permissions.get_groups())


@hook.command("gperms", permissions=["permissions_users"])
async def get_group_permissions(text, conn, notice):
    """<group> - lists permissions given to <group>"""
    group = text.strip()
    permission_manager = conn.permissions
    if not permission_manager.group_exists(group):
        notice("Unknown group '{}'".format(group))
        return None

    group_permissions = permission_manager.get_group_permissions(group.lower())
    if group_permissions:
        return "Group {} has permissions {}".format(group, group_permissions)

    return "Group {} exists, but has no permissions".format(group)


@hook.command("gusers", permissions=["permissions_users"])
async def get_group_users(text, conn, notice):
    """<group> - lists users in <group>"""
    group = text.strip()
    permission_manager = conn.permissions
    if not permission_manager.group_exists(group):
        notice("Unknown group '{}'".format(group))
        return None

    group_users = permission_manager.get_group_users(group.lower())
    if group_users:
        return "Group {} has members: {}".format(group, group_users)

    return "Group {} exists, but has no members".format(group)


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
async def get_user_permissions(event):
    """[user] - lists all permissions given to [user], or the caller if no user is specified"""
    user = parse_self(event)
    if not user:
        return None

    permission_manager = event.conn.permissions

    user_permissions = permission_manager.get_user_permissions(user.lower())
    if user_permissions:
        return "User {} has permissions: {}".format(user, user_permissions)

    return "User {} has no elevated permissions".format(user)


@hook.command("ugroups", autohelp=False)
async def get_user_groups(event):
    """[user] - lists all permissions given to [user], or the caller if no user is specified"""
    user = parse_self(event)
    if not user:
        return None

    permission_manager = event.conn.permissions

    user_groups = permission_manager.get_user_groups(user.lower())
    if user_groups:
        return "User {} is in groups: {}".format(user, user_groups)

    return "User {} is in no permission groups".format(user)


def remove_user_from_group(user, group, event):
    permission_manager = event.conn.permissions
    changed_masks = permission_manager.remove_group_user(
        group.lower(), user.lower()
    )

    mask_list = formatting.get_text_list(changed_masks, "and")
    event.reply("Removed {} from {}".format(mask_list, group))
    event.admin_log(
        "{} used deluser remove {} from {}.".format(
            event.nick, mask_list, group
        )
    )

    return bool(changed_masks)


@hook.command("deluser", permissions=["permissions_users"])
async def remove_permission_user(text, event, bot, conn, notice, reply):
    """<user> [group] - removes <user> from [group], or from all groups if no group is specified"""
    split = text.split()
    if len(split) > 2:
        notice("Too many arguments")
        return

    if not split:
        notice("Not enough arguments")
        return

    perm_manager = conn.permissions
    user = split[0]
    if len(split) > 1:
        group = split[1]

        if group and not perm_manager.group_exists(group.lower()):
            notice("Unknown group '{}'".format(group))
            return

        groups = [group] if perm_manager.user_in_group(user, group) else []
    else:
        group = None
        groups = perm_manager.get_user_groups(user.lower())

    if not groups:
        reply("No masks with elevated permissions matched {}".format(user))
        return

    changed = False
    for group in groups:
        if remove_user_from_group(user, group, event):
            changed = True

    if changed:
        bot.config.save_config()
        perm_manager.reload()


@hook.command("adduser", permissions=["permissions_users"])
async def add_permissions_user(text, nick, conn, bot, notice, reply, admin_log):
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

    if not permission_manager.add_user_to_group(user.lower(), group.lower()):
        reply("User {} is already matched in group {}".format(user, group))
        return None

    if group_exists:
        reply("User {} added to group {}".format(user, group))
        admin_log("{} used adduser to add {} to {}.".format(nick, user, group))
    else:
        reply("Group {} created with user {}".format(group, user))
        admin_log(
            "{} used adduser to create group {} and add {} to it.".format(
                nick, group, user
            )
        )

    bot.config.save_config()
    permission_manager.reload()


@hook.command("stopthebot", permissions=["botcontrol"])
async def stop(text, bot):
    """[reason] - stops me with [reason] as its quit message."""
    if text:
        await bot.stop(reason=text)
    else:
        await bot.stop()


@hook.command(permissions=["botcontrol"])
async def restart(text, bot):
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
async def join(text, conn, nick, notice, admin_log):
    """<channel> [key] - joins <channel> with the optional [key]"""
    parts = text.split(None, 1)
    target = parts.pop(0)

    if parts:
        key = parts.pop(0)
    else:
        key = None

    if not target.startswith("#"):
        target = "#{}".format(target)

    admin_log("{} used JOIN to make me join {}.".format(nick, target))
    notice("Attempting to join {}...".format(target))
    conn.join(target, key)


def parse_targets(text, chan):
    if text:
        targets = text
    else:
        targets = chan

    return targets.split()


@hook.command(permissions=["botcontrol", "snoonetstaff"], autohelp=False)
async def part(text, conn, nick, chan, notice, admin_log):
    """[#channel] - parts [#channel], or the caller's channel if no channel is specified"""
    for target in parse_targets(text, chan):
        admin_log("{} used PART to make me leave {}.".format(nick, target))
        notice("Attempting to leave {}...".format(target))
        conn.part(target)


@hook.command(autohelp=False, permissions=["botcontrol"])
async def cycle(text, conn, chan, notice):
    """[#channel] - cycles [#channel], or the caller's channel if no channel is specified"""
    for target in parse_targets(text, chan):
        notice("Attempting to cycle {}...".format(target))
        conn.part(target)
        conn.join(target)


@hook.command("nick", permissions=["botcontrol"])
async def change_nick(text, conn, notice, is_nick_valid):
    """<nick> - changes my nickname to <nick>"""
    if not is_nick_valid(text):
        notice("Invalid username '{}'".format(text))
        return

    notice("Attempting to change nick to '{}'...".format(text))
    conn.target_nick = text
    conn.set_nick(text)


@hook.command(permissions=["botcontrol"])
async def raw(text, conn, notice):
    """<command> - sends <command> as a raw IRC command"""
    notice("Raw command sent.")
    conn.send(text)


def get_chan(chan, text):
    stripped_text = text.strip()
    if stripped_text.startswith("#") and " " in stripped_text:
        return tuple(stripped_text.split(None, 1))

    return chan, stripped_text


@hook.command(permissions=["botcontrol", "snoonetstaff"])
async def say(text, conn, chan, nick, admin_log):
    """[#channel] <message> - says <message> to [#channel], or to the caller's channel if no channel is specified"""
    channel, text = get_chan(chan, text)
    admin_log(
        '{} used SAY to make me SAY "{}" in {}.'.format(nick, text, channel)
    )
    conn.message(channel, text)


@hook.command("message", "sayto", permissions=["botcontrol", "snoonetstaff"])
async def send_message(text, conn, nick, admin_log):
    """<name> <message> - says <message> to <name>"""
    split = text.split(None, 1)
    channel = split[0]
    text = split[1]
    admin_log(
        '{} used MESSAGE to make me SAY "{}" in {}.'.format(nick, text, channel)
    )
    conn.message(channel, text)


@hook.command("me", "act", permissions=["botcontrol", "snoonetstaff"])
async def me(
    text: str, conn: IrcClient, chan: str, nick: str, event: CommandEvent
) -> None:
    """
    [#channel] <action> - acts out <action> in a [#channel], or in the current channel of none is specified
    """
    channel, text = get_chan(chan, text)
    event.admin_log(
        '{} used ME to make me ACT "{}" in {}.'.format(nick, text, channel)
    )
    conn.ctcp(channel, "ACTION", text)


@hook.command(autohelp=False, permissions=["botcontrol"])
async def listchans(conn, chan, message, notice):
    """- Lists the current channels the bot is in"""
    chans = ", ".join(sorted(conn.channels, key=lambda x: x.strip("#").lower()))
    lines = formatting.chunk_str("I am currently in: {}".format(chans))
    func = notice if chan[:1] == "#" else message
    for line in lines:
        func(line)
