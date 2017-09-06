import asyncio
import logging
from functools import partial

from cloudbot import hook
from cloudbot.event import CapEvent

logger = logging.getLogger("cloudbot")


@asyncio.coroutine
def handle_available_caps(conn, caplist, event, irc_paramlist, bot):
    available_caps = conn.memory.setdefault("available_caps", set())
    caps = [tuple(cap.split('=', 1)) for cap in caplist]
    available_caps.update(caps)
    cap_queue = conn.memory.setdefault("cap_queue", {})
    for cap, *param in caps:
        cap_event = partial(CapEvent, base_event=event, cap=cap, cap_param=param[0] if param else None)
        tasks = [
            bot.plugin_manager.launch(_hook, cap_event(hook=_hook))
            for _hook in bot.plugin_manager.cap_hooks["on_available"][cap.casefold()]
        ]
        results = yield from asyncio.gather(*tasks)
        if any(results):
            cap_queue[cap.casefold()] = conn.loop.create_future()
            conn.cmd("CAP", "REQ", cap)

    if irc_paramlist[2] != '+':
        yield from asyncio.gather(*cap_queue.values())
        cap_queue.clear()
        conn.send("CAP END")


@asyncio.coroutine
@hook.irc_raw("CAP")
def on_cap(irc_paramlist, conn, bot, event):
    caplist = []
    if len(irc_paramlist) > 2:
        capstr = irc_paramlist[-1].strip()
        if capstr[0] == ':':
            capstr = capstr[1:]

        caplist = capstr.split()
    subcmd = irc_paramlist[1].upper()
    if subcmd == "LS":
        yield from handle_available_caps(conn, caplist, event, irc_paramlist, bot)

    elif subcmd in ('ACK', 'NAK'):
        enabled = subcmd == 'ACK'
        server_caps = conn.memory.setdefault('server_caps', {})
        cap_queue = conn.memory.get("cap_queue", {})
        caps = [cap.casefold() for cap in caplist]
        for cap in caps:
            server_caps[cap] = enabled
            if enabled:
                cap_event = partial(CapEvent, base_event=event, cap=cap)
                tasks = [
                    bot.plugin_manager.launch(_hook, cap_event(hook=_hook))
                    for _hook in bot.plugin_manager.cap_hooks["on_ack"][cap]
                ]
                yield from asyncio.gather(*tasks)

            if cap in cap_queue:
                cap_queue[cap].set_result(enabled)

    elif subcmd == 'LIST':
        logger.info("Enabled Capabilities: %s", irc_paramlist[-1])
    elif subcmd == 'NEW':
        logger.info("New capabilities advertised: %s", irc_paramlist[-1])
        yield from handle_available_caps(conn, caplist, event, irc_paramlist, bot)
    elif subcmd == 'DEL':
        logger.info("Capabilities removed by server: %s", irc_paramlist[-1])
        server_caps = conn.memory.setdefault('server_caps', {})
        for cap in caplist:
            server_caps[cap] = False
