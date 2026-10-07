"""
Tracks various server info like ISUPPORT tokens
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import TYPE_CHECKING, TypeVar

import attrs

from cloudbot import hook
from cloudbot.util.extensible_data import ExtItem
from cloudbot.util.irc import ChannelMode, ModeType, StatusMode

if TYPE_CHECKING:
    from collections.abc import Callable

    from cloudbot.bot import CloudBot
    from cloudbot.client import Client

DEFAULT_STATUS = (
    StatusMode.make("@", "o", 2),
    StatusMode.make("+", "v", 1),
)


@attrs.define
class ServerInfo:
    isupport_tokens: dict[str, str | None] = attrs.field(factory=dict)
    statuses: dict[str, StatusMode] = attrs.field(factory=dict)
    channel_modes: dict[str, ChannelMode] = attrs.field(factory=dict)
    extbans: str | None = None
    extban_prefix: str | None = None


class ServerInfoExtItem(ExtItem[ServerInfo]):
    def __init__(self) -> None:
        super().__init__("server_info", ephemeral=True)

    def create(self) -> ServerInfo:
        return ServerInfo()


ServerInfoExt = ServerInfoExtItem()


@hook.on_start()
def do_isupport(bot: CloudBot) -> None:
    for conn in bot.connections.values():
        if conn.connected:
            clear_isupport(conn)
            conn.send("VERSION")


@hook.connect()
def clear_isupport(conn: Client) -> None:
    serv_info = get_server_info(conn)
    statuses: dict[str, StatusMode] = get_status_modes(serv_info, clear=True)
    for s in DEFAULT_STATUS:
        statuses[s.prefix] = s
        statuses[s.character] = s

    get_channel_modes(serv_info, clear=True)

    isupport_data = serv_info.isupport_tokens
    isupport_data.clear()


K = TypeVar("K")
V = TypeVar("V", bound=MutableMapping)


def get_server_info(conn: Client) -> ServerInfo:
    return ServerInfoExt.ensure(conn)


def get_status_modes(
    serv_info: ServerInfo, *, clear: bool = False
) -> dict[str, StatusMode]:
    statuses = serv_info.statuses
    if clear:
        statuses.clear()

    return statuses


def get_channel_modes(
    serv_info: ServerInfo, *, clear: bool = False
) -> dict[str, ChannelMode]:
    modes = serv_info.channel_modes
    if clear:
        modes.clear()

    return modes


def sync_statuses(serv_info: ServerInfo) -> None:
    """
    Copy channel status modes to the modelist
    """
    statuses = get_status_modes(serv_info)
    modes = get_channel_modes(serv_info)

    for status in statuses.values():
        modes[status.character] = status


def handle_prefixes(data: str | None, serv_info: ServerInfo) -> None:
    statuses = get_status_modes(serv_info, clear=True)
    if data is None:
        return

    modes, prefixes = data.split(")", 1)
    modes = modes.strip("(")
    parsed = enumerate(reversed(list(zip(modes, prefixes))))
    for lvl, (mode, prefix) in parsed:
        status = StatusMode.make(prefix, mode, lvl + 1)
        statuses[status.prefix] = status
        statuses[status.character] = status

    sync_statuses(serv_info)


def handle_chan_modes(value: str | None, serv_info: ServerInfo) -> None:
    types = "ABCD"
    modelist = get_channel_modes(serv_info, clear=True)
    if value is None:
        return

    for i, modes in enumerate(value.split(",")):
        if i >= len(types):
            break

        for mode in modes:
            modelist[mode] = ChannelMode(mode, ModeType(types[i]))

    sync_statuses(serv_info)


def handle_extbans(value: str | None, serv_info: ServerInfo) -> None:
    if value is None:
        return

    pfx, extbans = value.split(",", 1)
    serv_info.extbans = extbans
    serv_info.extban_prefix = pfx


isupport_handlers: dict[str, Callable[[str | None, ServerInfo], None]] = {
    "PREFIX": handle_prefixes,
    "CHANMODES": handle_chan_modes,
    "EXTBAN": handle_extbans,
}


@hook.irc_raw("005", singlethread=True)
def on_isupport(conn: Client, irc_paramlist: list[str]) -> None:
    serv_info = get_server_info(conn)
    token_data = serv_info.isupport_tokens
    # strip the nick and trailing ':are supported by this server' message
    tokens = irc_paramlist[1:-1]
    for token in tokens:
        name, _, value = token.partition("=")
        name = name.upper()
        token_data[name] = value or None
        handler = isupport_handlers.get(name)
        if handler:
            handler(value, serv_info)
