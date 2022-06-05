from cloudbot import hook


@hook.irc_raw('366')
def setmodes(conn, reply):
    botnick = conn.config["nick"]
    conn.cmd("MODE", botnick, "+BD")
