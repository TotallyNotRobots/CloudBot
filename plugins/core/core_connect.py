from cloudbot import hook


@hook.connect(priority=0, clients="irc")
def conn_pass(conn):
    conn.set_pass(conn.config["connection"].get("password"))


@hook.connect(priority=10)
def conn_nick(conn):
    conn.nick = conn.target_nick
    conn.set_nick(conn.nick)


@hook.connect(priority=20, clients="irc")
def conn_user(conn, bot):
    conn.cmd(
        "USER",
        conn.config.get("user", "cloudbot"),
        "3",
        "*",
        conn.config.get("realname", "CloudBot - {repo_link}").format(
            repo_link=bot.repo_link
        ),
    )
