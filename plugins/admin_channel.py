from cloudbot import hook


def mode_cmd(mode, text, text_inp, chan, conn, notice, nick, admin_log):
    """ generic mode setting function """
    split = text_inp.split(" ")
    if split[0].startswith("#"):
        channel = split[0]
        target = split[1]
        notice("Attempting to {} {} in {}...".format(text, target, channel))
        admin_log("{} used {} to set {} on {} in {}.".format(nick, text, mode, target, channel))
        conn.send("MODE {} {} {}".format(channel, mode, target))
    else:
        channel = chan
        target = split[0]
        notice("Attempting to {} {} in {}...".format(text, target, channel))
        admin_log("{} used {} to set {} on {} in {}.".format(nick, text, mode, target, channel))
        conn.send("MODE {} {} {}".format(channel, mode, target))


def mode_cmd_no_target(mode, text, text_inp, chan, conn, notice, nick, admin_log):
    """ generic mode setting function without a target"""
    split = text_inp.split(" ")
    if split[0].startswith("#"):
        channel = split[0]
        notice("Attempting to {} {}...".format(text, channel))
        admin_log("{} used {} to set {} in {}.".format(nick, text, mode, channel))
        conn.send("MODE {} {}".format(channel, mode))
    else:
        channel = chan
        notice("Attempting to {} {}...".format(text, channel))
        admin_log("{} used {} to set {} in {}.".format(nick, text, mode, channel))
        conn.send("MODE {} {}".format(channel, mode))


@hook.command(permissions=["op_ban", "op"])
def ban(text, conn, chan, notice, nick, admin_log):
    """[channel] <user> - bans <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("+b", "ban", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_ban", "op"])
def unban(text, conn, chan, notice, nick, admin_log):
    """[channel] <user> - unbans <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("-b", "unban", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_quiet", "op"])
def quiet(text, conn, chan, notice, nick, admin_log):
    """[channel] <user> - quiets <user> in [channel], or in the caller's channel if no channel is specified"""
    if conn.name == "snoonet":
        out = "mode {} +b m:{}".format(chan, text)
        conn.send(out)
        return
    mode_cmd("+q", "quiet", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_quiet", "op"])
def unquiet(text, conn, chan, notice, nick, admin_log):
    """[channel] <user> - unquiets <user> in [channel], or in the caller's channel if no channel is specified"""
    if conn.name == "snoonet":
        out = "mode {} -b m:{}".format(chan, text)
        conn.send(out)
        return
    mode_cmd("-q", "unquiet", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_voice", "op"])
def voice(text, conn, chan, notice, nick, admin_log):
    """[channel] <user> - voices <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("+v", "voice", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_voice", "op"])
def devoice(text, conn, chan, notice, nick, admin_log):
    """[channel] <user> - devoices <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("-v", "devoice", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_op", "op"])
def op(text, conn, chan, notice, nick, admin_log):
    """[channel] <user> - ops <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("+o", "op", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_op", "op"])
def deop(text, conn, chan, notice, nick, admin_log):
    """[channel] <user> - deops <user> in [channel], or in the caller's channel if no channel is specified"""
    mode_cmd("-o", "deop", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_topic", "op"])
def topic(text, conn, chan, nick, admin_log):
    """[channel] <topic> - changes the topic to <topic> in [channel], or in the caller's channel
     if no channel is specified"""
    split = text.split(" ")
    if split[0].startswith("#"):
        msg = " ".join(split[1:])
        chan = split[0]
    else:
        msg = " ".join(split)

    admin_log("{} used TOPIC to set the topic in {} to {}.".format(nick, chan, msg))
    conn.send("TOPIC {} :{}".format(chan, msg))


@hook.command(permissions=["op_kick", "op"])
def kick(text, chan, conn, notice, nick, admin_log):
    """[channel] <user> - kicks <user> from [channel], or from the caller's channel if no channel is specified"""
    split = text.split(" ")

    if split[0].startswith("#"):
        channel = split[0]
        target = split[1]
        if len(split) > 2:
            reason = " ".join(split[2:])
            out = "KICK {} {}: {}".format(channel, target, reason)
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

    notice("Attempting to kick {} from {}...".format(target, channel))
    admin_log("{} used KICK to kick {} in {}.".format(nick, target, channel))
    conn.send(out)


@hook.command(permissions=["op_rem", "op"])
def remove(text, chan, conn, nick, admin_log):
    """<user> - force removes <user> from the caller's channel."""
    split = text.split(" ")
    user = split[0]
    if len(split) > 1:
        reason = " ".join(split[1:]) + " requested by {}".format(nick)
    else:
        reason = "requested by {}.".format(nick)
    out = "REMOVE {} {} :{}".format(user, chan, reason)
    admin_log("{} used REMOVE on {} in {} with reason {}.".format(nick, user, chan, reason))
    conn.send(out)


@hook.command(permissions=["op_mute", "op"], autohelp=False)
def mute(text, conn, chan, notice, nick, admin_log):
    """[channel] - mutes [channel], or in the caller's channel if no channel is specified"""
    mode_cmd_no_target("+m", "mute", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_mute", "op"], autohelp=False)
def unmute(text, conn, chan, notice, nick, admin_log):
    """[channel] - unmutes [channel], or in the caller's channel if no channel is specified"""
    mode_cmd_no_target("-m", "unmute", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_lock", "op"], autohelp=False)
def lock(text, conn, chan, notice, nick, admin_log):
    """[channel] - locks [channel], or in the caller's channel if no channel is specified"""
    mode_cmd_no_target("+i", "lock", text, chan, conn, notice, nick, admin_log)


@hook.command(permissions=["op_lock", "op"], autohelp=False)
def unlock(text, conn, chan, notice, nick, admin_log):
    """[channel] - unlocks [channel], or in the caller's channel if no channel is specified"""
    mode_cmd_no_target("-i", "unlock", text, chan, conn, notice, nick, admin_log)
