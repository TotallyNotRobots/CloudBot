from __future__ import annotations

import asyncio
import logging
from collections import ChainMap
from functools import partial
from typing import TYPE_CHECKING, Any

import attrs
from irclib.parser import CapList

from cloudbot import hook
from cloudbot.event import CapEvent
from cloudbot.util import async_util
from cloudbot.util.extensible_data import ExtItem

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot
    from cloudbot.client import Client
    from cloudbot.clients.irc import IrcClient
    from cloudbot.event import Event

logger = logging.getLogger("cloudbot")


@attrs.define
class CapInfo:
    available_caps: CapList = attrs.field(factory=CapList)
    cap_queue: dict[str, asyncio.Future[bool]] = attrs.field(factory=dict)
    server_caps: dict[str, bool] = attrs.field(factory=dict)


class CapInfoExtItem(ExtItem[CapInfo]):
    def __init__(self) -> None:
        super().__init__("cap_info", ephemeral=True)

    def create(self) -> CapInfo:
        return CapInfo()


CapInfoExt = CapInfoExtItem()


@hook.connect(priority=-10, clients="irc")
def send_cap_ls(conn: IrcClient) -> None:
    conn.cmd("CAP", "LS", "302")
    info = CapInfoExt.ensure(conn)

    for fut in info.cap_queue.values():
        if not fut.done():
            fut.cancel()

    info.available_caps.clear()
    info.cap_queue.clear()


async def handle_available_caps(
    conn: IrcClient,
    caplist: CapList,
    event: Event,
    irc_paramlist: list[str],
    bot: CloudBot,
) -> None:
    info = CapInfoExt.ensure(conn)
    info.available_caps.extend(caplist)
    for cap in caplist:
        name = cap.name
        name_cf = name.casefold()
        cap_event = partial(
            CapEvent, base_event=event, cap=name, cap_param=cap.value
        )

        tasks = [
            bot.plugin_manager.internal_launch(_hook, cap_event(hook=_hook))
            for _hook in bot.plugin_manager.cap_hooks["on_available"][name_cf]
        ]

        results = await asyncio.gather(*tasks)
        if any(ok and (res or res is None) for ok, res in results):
            info.cap_queue[name_cf] = asyncio.Future[bool]()
            conn.cmd("CAP", "REQ", name)

    if irc_paramlist[2] != "*":
        await asyncio.gather(*info.cap_queue.values())
        info.cap_queue.clear()
        conn.send("CAP END")


HANDLERS = {}


def _subcmd_handler(*types: str):
    def _decorate(func):
        for subcmd in types:
            HANDLERS[subcmd.upper()] = func

        return func

    return _decorate


async def _launch_handler(subcmd: str, event: Event, **kwargs: Any) -> None:
    subcmd = subcmd.upper()
    kwargs["subcmd"] = subcmd
    try:
        handler = HANDLERS[subcmd]
    except LookupError:
        return

    await async_util.run_func_with_args(
        event.loop,
        handler,
        ChainMap(event, kwargs),  # type: ignore[arg-type]
    )


@_subcmd_handler("LS")
async def cap_ls(
    conn: IrcClient,
    caplist: CapList,
    event: Event,
    irc_paramlist: list[str],
    bot: CloudBot,
) -> None:
    logger.info("[%s|cap] Available capabilities: %s", conn.name, caplist)
    await handle_available_caps(conn, caplist, event, irc_paramlist, bot)


async def handle_req_resp(
    enabled: bool, conn: Client, caplist: CapList, event: Event, bot: CloudBot
) -> None:
    info = CapInfoExt.ensure(conn)
    for cap in (cap.name.casefold() for cap in caplist):
        info.server_caps[cap] = enabled
        if enabled:
            cap_event = partial(CapEvent, base_event=event, cap=cap)
            tasks = [
                bot.plugin_manager.launch(_hook, cap_event(hook=_hook))
                for _hook in bot.plugin_manager.cap_hooks["on_ack"][cap]
            ]

            await asyncio.gather(*tasks)

        if cap in info.cap_queue:
            info.cap_queue[cap].set_result(enabled)


@_subcmd_handler("ACK")
async def cap_ack_nak(
    conn: Client, caplist: CapList, event: Event, bot: CloudBot
) -> None:
    await handle_req_resp(True, conn, caplist, event, bot)


@_subcmd_handler("NAK")
async def cap_nak(
    conn: Client, caplist: CapList, event: Event, bot: CloudBot
) -> None:
    await handle_req_resp(False, conn, caplist, event, bot)


@_subcmd_handler("LIST")
def cap_list(caplist: CapList, conn: Client) -> None:
    logger.info("[%s|cap] Enabled Capabilities: %s", conn.name, caplist)


@_subcmd_handler("NEW")
async def cap_new(
    caplist: CapList,
    conn: IrcClient,
    event: Event,
    bot: CloudBot,
    irc_paramlist: list[str],
) -> None:
    logger.info("[%s|cap] New capabilities advertised: %s", conn.name, caplist)
    await handle_available_caps(conn, caplist, event, irc_paramlist, bot)


@_subcmd_handler("DEL")
def cap_del(conn: Client, caplist: CapList) -> None:
    # TODO add hooks for CAP removal
    logger.info(
        "[%s|cap] Capabilities removed by server: %s", conn.name, caplist
    )
    info = CapInfoExt.ensure(conn)
    for cap in caplist:
        info.server_caps[cap.name.casefold()] = False


@hook.irc_raw("CAP")
async def on_cap(irc_paramlist: list[str], event: Event) -> None:
    args = {}
    if len(irc_paramlist) > 2:
        args["caplist"] = CapList.parse(irc_paramlist[-1])

    await _launch_handler(irc_paramlist[1], event, **args)
