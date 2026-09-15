from __future__ import annotations

from typing import TYPE_CHECKING

from cloudbot import hook
from cloudbot.hook import Priority

if TYPE_CHECKING:
    from cloudbot.client import Client
    from cloudbot.clients.irc import IrcClient


@hook.on_connect(priority=Priority.HIGHEST)
def clear_exts(conn: Client) -> None:
    conn.clear_ephemeral_extents()


@hook.connect(priority=0, clients="irc")
def conn_pass(conn: IrcClient) -> None:
    conn.set_pass(conn.config["connection"].get("password"))


@hook.connect(priority=10, clients=["irc"])
def conn_nick(conn: IrcClient) -> None:
    conn.nick = conn.target_nick
    conn.set_nick(conn.nick)


@hook.connect(priority=20, clients="irc")
def conn_user(conn: IrcClient, bot) -> None:
    conn.cmd(
        "USER",
        conn.config.get("user", "cloudbot"),
        "3",
        "*",
        conn.config.get("realname", "CloudBot - {repo_link}").format(
            repo_link=bot.repo_link
        ),
    )
