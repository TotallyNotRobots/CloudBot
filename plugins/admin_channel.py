from cloudbot import hook

# Messages
NO_MODE = "Mode character {char!r} does not seem to exist on this network."
MODE_CMD_LOG = "{nick} used {cmd} to set {mode} on {target} in {channel}."
MODE_CMD_NO_TARGET_LOG = "{nick} used {cmd} to set {mode} in {channel}."
TOPIC_CHANGE = "{nick} used TOPIC to set the topic in {channel} to {text}."
KICK_LOG = "{nick} used KICK to kick {target} in {channel}."
REMOVE_LOG = "{nick} used REMOVE on {target} in {channel} because {reason!r}."


def check_for_chan_mode(char, mode_warn, event):
    serv_info = event.conn.memory["server_info"]
    modes = serv_info.get("channel_modes", "")
    status = serv_info.get("statuses", [])
    if char in modes or char in status:
        return True

    if mode_warn:
        event.notice(NO_MODE.format(char=char))

    return False


def mode_cmd(mode, action, param, event, mode_warn=True):
    """generic mode setting function"""
    chan = event.chan
    nick = event.nick
    if not check_for_chan_mode(mode[1], mode_warn, event):
        return False

    split = param.split(" ")
    if split[0].startswith("#"):
        channel = split[0]
        target = split[1]
    else:
        channel = chan
        target = split[0]

    event.notice("Attempting to {} {} in {}...".format(action, target, channel))
    event.admin_log(
        MODE_CMD_LOG.format(
            nick=nick,
            cmd=action,
            mode=mode,
            target=target,
            channel=channel,
        )
    )
    event.conn.send("MODE {} {} {}".format(channel, mode, target))

    return True


def mode_cmd_no_target(mode, action, param, event, mode_warn=True):
    """generic mode setting function without a target"""
    chan = event.chan
    if not check_for_chan_mode(mode[1], mode_warn, event):
        return False

    split = param.split(" ")
    if split[0].startswith("#"):
        channel = split[0]
    else:
        channel = chan

    event.notice("Attempting to {} {}...".format(action, channel))
    event.admin_log(
        MODE_CMD_NO_TARGET_LOG.format(
            nick=event.nick,
            cmd=action,
            mode=mode,
            channel=channel,
        )
    )
    event.conn.send("MODE {} {}".format(channel, mode))
    return True


def do_extban(char, action, param, event, adding=True):
    serv_info = event.conn.memory["server_info"]
    if char not in serv_info.get("extbans", ""):
        return False

    extban_pfx = serv_info["extban_prefix"]

    split = param.split(" ")
    if split[0].startswith("#"):
        channel = split[0]
        target = split[1]
        param = "{} {}{}:{}".format(channel, extban_pfx, char, target)
    else:
        target = split[0]
        param = "{}{}:{}".format(extban_pfx, char, target)

    mode_cmd("+b" if adding else "-b", action, param, event)
    return True


@hook.command(permissions=["op_ban", "op", "chanop"])
def ban(text, event):
    """[channel] <user> - bans <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("+b", "ban", text, event)


@hook.command(permissions=["op_ban", "op", "chanop"])
def unban(text, event):
    """[channel] <user> - unbans <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("-b", "unban", text, event)


@hook.command(permissions=["op_quiet", "op", "chanop"])
def quiet(text, event):
    """[channel] <user> - quiets <user> in [channel], or in the caller's channel if no channel is specified"""
    if mode_cmd("+q", "quiet", text, event, False):
        return

    if not do_extban("m", "quiet", text, event, True):
        event.notice("Unable to set +q or a mute extban on this network.")


@hook.command(permissions=["op_quiet", "op", "chanop"])
def unquiet(text, event):
    """[channel] <user> - unquiets <user> in [channel], or in the caller's channel if no channel is specified"""
    if mode_cmd("-q", "unquiet", text, event, False):
        return

    if not do_extban("m", "unquiet", text, event, False):
        event.notice("Unable to unset +q or a mute extban on this network.")


@hook.command(permissions=["op_voice", "op", "chanop"])
def voice(text, event):
    """[channel] <user> - voices <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("+v", "voice", text, event)


@hook.command(permissions=["op_voice", "op", "chanop"])
def devoice(text, event):
    """[channel] <user> - devoices <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("-v", "devoice", text, event)


@hook.command(permissions=["op_op", "op", "chanop"])
def op(text, event):
    """[channel] <user> - ops <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("+o", "op", text, event)


@hook.command(permissions=["op_op", "op", "chanop"])
def deop(text, event):
    """[channel] <user> - deops <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("-o", "deop", text, event)


@hook.command(permissions=["op_topic", "op", "chanop"])
def topic(text, conn, chan, nick, event):
    """[channel] <topic> - changes the topic to <topic> in [channel], or in the caller's channel
    if no channel is specified"""
    split = text.split(" ")
    if split[0].startswith("#"):
        msg = " ".join(split[1:])
        chan = split[0]
    else:
        msg = " ".join(split)

    event.admin_log(TOPIC_CHANGE.format(nick=nick, channel=chan, text=msg))
    conn.send("TOPIC {} :{}".format(chan, msg))


@hook.command(permissions=["op_kick", "op", "chanop"])
def kick(text, chan, conn, nick, event):
    """[channel] <user> - kicks <user> from [channel], or from the caller's channel if no channel is specified"""
    split = text.split(" ")

    if split[0].startswith("#"):
        channel = split[0]
        target = split[1]
        if len(split) > 2:
            reason = " ".join(split[2:])
            out = "KICK {} {} :{}".format(channel, target, reason)
        else:
            out = "KICK {} {}".format(channel, target)
    else:
        channel = chan
        target = split[0]
        if len(split) > 1:
            reason = " ".join(split[1:])
            out = "KICK {} {} :{}".format(channel, target, reason)
        else:
            out = "KICK {} {}".format(channel, target)

    event.notice("Attempting to kick {} from {}...".format(target, channel))
    event.admin_log(KICK_LOG.format(nick=nick, target=target, channel=channel))
    conn.send(out)


@hook.command(permissions=["op_rem", "op", "chanop"])
def remove(text, chan, conn, nick, event):
    """<user> - force removes <user> from the caller's channel."""
    split = text.split(" ")
    user = split[0]
    if len(split) > 1:
        reason = " ".join(split[1:]) + " requested by {}".format(nick)
    else:
        reason = "requested by {}.".format(nick)
    out = "REMOVE {} {} :{}".format(user, chan, reason)
    event.admin_log(
        REMOVE_LOG.format(nick=nick, target=user, channel=chan, reason=reason)
    )
    conn.send(out)


@hook.command(permissions=["op_mute", "op", "chanop"], autohelp=False)
def mute(text, event):
    """[channel] - mutes [channel], or in the caller's channel if no channel is specified"""
    mode_cmd_no_target("+m", "mute", text, event)


@hook.command(permissions=["op_mute", "op", "chanop"], autohelp=False)
def unmute(text, event):
    """[channel] - unmutes [channel], or in the caller's channel if no channel is specified"""
    mode_cmd_no_target("-m", "unmute", text, event)


@hook.command(permissions=["op_lock", "op", "chanop"], autohelp=False)
def lock(text, event):
    """[channel] - locks [channel], or in the caller's channel if no channel is specified"""
    mode_cmd_no_target("+i", "lock", text, event)


@hook.command(permissions=["op_lock", "op", "chanop"], autohelp=False)
def unlock(text, event):
    """[channel] - unlocks [channel], or in the caller's channel if no channel is specified"""
    mode_cmd_no_target("-i", "unlock", text, event)
