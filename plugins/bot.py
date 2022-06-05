from cloudbot import hook


@hook.irc_raw('376')
def clear_isupport(conn):
    botnick = conn.config["name"]
    conn.cmd("MODE", botnick, "+B")
    conn.cmd("MODE", botnick, "+D")
