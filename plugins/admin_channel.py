import asyncio
from collections import namedtuple
from enum import Enum

from cloudbot import hook


class Mode(namedtuple('_Mode', 'char name unset_name')):
    def set(self, *, adding=True, name=None, param=None):
        if name is None:
            name = self.name if adding else self.unset_name

        return ModeSetting(self, adding, name, "" if param is None else param)


class ModeSetting(namedtuple('_ModeSetting', 'mode adding action parameter')):
    def __str__(self):
        return "{}{}".format('+' if self.adding else '-', self.mode.char)


ExtBan = namedtuple('ExtBan', 'char name unset_name')


class Modes(Mode, Enum):
    BAN = Mode('b', 'ban', 'unban')
    VOICE = Mode('v', 'voice', 'devoice')
    OP = Mode('o', 'op', 'deop')
    QUIET = Mode('q', 'quiet', 'unquiet')
    LOCK = Mode('i', 'lock', 'unlock')
    MUTE = Mode('m', 'mute', 'unnute')


class ExtBans(ExtBan, Enum):
    MUTE = ExtBan('m', 'quiet', 'unquiet')


def check_for_chan_mode(char, mode_warn, event):
    """
    :type char: str
    :type mode_warn: bool
    :type event: cloudbot.event.CommandEvent
    """
    serv_info = event.conn.memory["server_info"]
    modes = serv_info.get("channel_modes", "")
    status = serv_info.get("statuses", [])
    if char in modes or char in status:
        return True

    if mode_warn:
        event.notice("Mode character '{}' does not seem to exist on this network.".format(char))

    return False


def parse_chan_with_args(event, *, text=None, chan=None):
    """
    :type event: cloudbot.event.CommandEvent
    :type text: str
    :type chan: str
    """
    if chan is None:
        chan = event.chan

    if text is None:
        text = event.text

    split = text.split(None, 1)
    if event.is_channel(split[0]) and len(split) > 1:
        chan = split[0]
        text = split[1]

    return chan, text


@asyncio.coroutine
def check_perms(event, chan, *, perms=None):
    """
    :type event: cloudbot.event.Event
    :type chan: str
    :type perms: list[str]
    """
    if perms is None:
        perms = event.hook.permissions

    old_chan = event.chan
    try:
        event.chan = chan
        return (yield from event.check_permissions(*perms))
    finally:
        event.chan = old_chan


@asyncio.coroutine
def pre_mode_checks(mode, event, text, chan, mode_warn):
    """
    :type mode: ModeSetting
    :type event: cloudbot.event.CommandEvent
    :type text: str
    :type chan: str
    :type mode_warn: bool
    """
    if not check_for_chan_mode(mode.mode.char, mode_warn, event):
        return False

    channel, target = parse_chan_with_args(event, text=text, chan=chan)
    has_perm = yield from check_perms(event, channel)
    if not has_perm:
        event.notice("You do not have permission to do that")
        return True

    return channel, target


@asyncio.coroutine
def mode_cmd(mode, event, *, text=None, chan=None, mode_warn=True):
    """ generic mode setting function
    :type mode: ModeSetting
    :type event: cloudbot.event.CommandEvent
    :type text: str
    :type chan: str
    :type mode_warn: bool
    """
    res = yield from pre_mode_checks(mode, event, text, chan, mode_warn)
    if res is True or res is False:
        return res

    channel, target = res

    event.notice("Attempting to {} {} in {}...".format(mode.action, target, channel))
    event.admin_log("{} used {} to set {} on {} in {}.".format(event.nick, mode.action, mode, target, channel))
    event.conn.send("MODE {} {} {}".format(channel, mode, target))

    return True


@asyncio.coroutine
def mode_cmd_no_target(mode, event, *, text=None, chan=None, mode_warn=True):
    """ generic mode setting function without a target
    :type mode: ModeSetting
    :type text: str
    :type chan: str
    :type event: cloudbot.event.CommandEvent
    :type mode_warn: bool
    """
    res = yield from pre_mode_checks(mode, event, text, chan, mode_warn)
    if res is True or res is False:
        return res

    channel, _ = res

    event.notice("Attempting to {} {}...".format(mode.action, channel))
    event.admin_log("{} used {} to set {} in {}.".format(event.nick, mode.action, mode, channel))
    event.conn.send("MODE {} {}".format(channel, mode))
    return True


@asyncio.coroutine
def do_extban(extban, event, *, adding=True):
    """
    :type extban: ExtBan
    :type event: cloudbot.event.CommandEvent
    :type adding: bool
    """

    serv_info = event.conn.memory["server_info"]
    if extban.char not in serv_info.get("extbans", ""):
        return False

    extban_pfx = serv_info["extban_prefix"]

    channel, target = parse_chan_with_args(event)
    fmt = "{}{}:{}".format(extban_pfx, extban.char, target)

    return (yield from mode_cmd(
        Modes.BAN.set(adding=adding), event, text=fmt, chan=channel
    ))


@hook.command(permissions=["op_ban", "op", "chanop"], clients='irc')
@asyncio.coroutine
def ban(event):
    """[channel] <user> - bans <user> in [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd(Modes.BAN.set(), event)


@hook.command(permissions=["op_ban", "op", "chanop"], clients='irc')
@asyncio.coroutine
def unban(event):
    """[channel] <user> - unbans <user> in [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd(Modes.BAN.set(adding=False), event)


@hook.command(permissions=["op_voice", "op", "chanop"], clients='irc')
@asyncio.coroutine
def voice(event):
    """[channel] <user> - voices <user> in [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd(Modes.VOICE.set(), event)


@hook.command(permissions=["op_voice", "op", "chanop"], clients='irc')
@asyncio.coroutine
def devoice(event):
    """[channel] <user> - devoices <user> in [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd(Modes.VOICE.set(adding=False), event)


@hook.command(permissions=["op_op", "op", "chanop"], clients='irc')
@asyncio.coroutine
def op(event):
    """[channel] <user> - ops <user> in [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd(Modes.OP.set(), event)


@hook.command(permissions=["op_op", "op", "chanop"], clients='irc')
@asyncio.coroutine
def deop(event):
    """[channel] <user> - deops <user> in [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd(Modes.OP.set(adding=False), event)


@hook.command(permissions=["op_mute", "op", "chanop"], autohelp=False, clients='irc')
@asyncio.coroutine
def mute(event):
    """[channel] - mutes [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd_no_target(Modes.MUTE.set(), event)


@hook.command(permissions=["op_mute", "op", "chanop"], autohelp=False, clients='irc')
@asyncio.coroutine
def unmute(event):
    """[channel] - unmutes [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd_no_target(Modes.MUTE.set(adding=False), event)


@hook.command(permissions=["op_lock", "op", "chanop"], autohelp=False, clients='irc')
@asyncio.coroutine
def lock(event):
    """[channel] - locks [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd_no_target(Modes.LOCK.set(), event)


@hook.command(permissions=["op_lock", "op", "chanop"], autohelp=False, clients='irc')
@asyncio.coroutine
def unlock(event):
    """[channel] - unlocks [channel], or in the caller's channel if no channel is specified"""
    yield from mode_cmd_no_target(Modes.LOCK.set(adding=False), event)


@hook.command(permissions=["op_quiet", "op", "chanop"], clients='irc')
@asyncio.coroutine
def quiet(event):
    """[channel] <user> - quiets <user> in [channel], or in the caller's channel if no channel is specified"""
    if (yield from mode_cmd(Modes.QUIET.set(), event, mode_warn=False)):
        return

    if not (yield from do_extban(ExtBans.MUTE, event)):
        event.notice("Unable to set +q or a mute extban on this network.")


@hook.command(permissions=["op_quiet", "op", "chanop"], clients='irc')
@asyncio.coroutine
def unquiet(event):
    """[channel] <user> - unquiets <user> in [channel], or in the caller's channel if no channel is specified"""
    if (yield from mode_cmd(Modes.QUIET.set(adding=False), event, mode_warn=False)):
        return

    if not (yield from do_extban(ExtBans.MUTE, event, adding=False)):
        event.notice("Unable to unset +q or a mute extban on this network.")


@asyncio.coroutine
def do_command(cmd, event, action_text, cmd_fmt, target, *, text=None, channel=None):
    """
    :type cmd: str
    :type event: cloudbot.event.CommandEvent
    :type action_text: str
    :type cmd_fmt: str
    :type target: str
    :type text: str
    :type channel: str
    """
    if channel is None:
        channel = event.chan

    if not (yield from check_perms(event, channel)):
        event.notice("You do not have permission to do that")
        return

    notice_fmt = "Attempting to {action} {target} in {channel}..."

    log_fmt = "{actor} used {cmd} to {action} {target} in {channel}."

    event.notice(
        notice_fmt.format(
            action=action_text,
            target=target,
            channel=channel,
        )
    )

    event.admin_log(
        log_fmt.format(
            actor=event.nick,
            cmd=cmd,
            action=action_text,
            channel=channel
        )
    )

    event.conn.send(cmd_fmt.format(
        cmd=cmd,
        channel=channel,
        target=target,
        text=text,
    ))


@hook.command(permissions=["op_topic", "op", "chanop"], clients='irc')
@asyncio.coroutine
def topic(event):
    """[channel] <topic> - changes the topic to <topic> in [channel], or in the caller's channel if no channel is specified"""
    channel, msg = parse_chan_with_args(event)
    yield from do_command(
        "TOPIC", event, "set the topic to", "{cmd} {channel} :{target}", msg, channel=channel
    )


@asyncio.coroutine
def remove_user(cmd, action_text, event, *, fmt="{cmd} {channel} {target} :{text}"):
    """
    :type cmd: str
    :type action_text: str
    :type event: cloudbot.event.CommandEvent
    :type fmt: str
    """
    _, target = parse_chan_with_args(event)

    if ' ' in target:
        target, reason = target.split(None, 1)
    else:
        reason = None

    if reason is None:
        reason = "Requested by {event.nick}"
    else:
        reason += " (Requested by {event.nick})"

    reason = reason.format(event=event)

    yield from do_command(cmd.upper(), event, action_text, fmt, target=target, text=reason)


@hook.command(permissions=["op_kick", "op", "chanop"], clients='irc')
@asyncio.coroutine
def kick(event):
    """[channel] <user> [reason] - kicks <user> from [channel], or from the caller's channel if no channel is specified"""
    yield from remove_user("KICK", "kick", event)


@hook.command(permissions=["op_rem", "op", "chanop"], clients='irc')
@asyncio.coroutine
def remove(event):
    """[channel] <user> [reason] - force removes <user> from the caller's channel."""
    yield from remove_user("REMOVE", "remove", event, fmt="{cmd} {target} {channel} :{text}")
