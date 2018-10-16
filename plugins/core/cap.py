import asyncio
from collections import ChainMap
from functools import partial

from cloudbot import hook
from cloudbot.event import CapEvent
from cloudbot.util import async_util
from cloudbot.util.parsers.irc import CapList


@hook.connect(priority=-10, clients="irc")
def send_cap_ls(conn):
    conn.cmd("CAP", "LS", "302")
    conn.memory.setdefault("available_caps", set()).clear()
    conn.memory.setdefault("cap_queue", {}).clear()


@asyncio.coroutine
def handle_available_caps(conn, caplist, event, irc_paramlist, bot):
    available_caps = conn.memory["available_caps"]
    available_caps.update(caplist)
    cap_queue = conn.memory["cap_queue"]
    for cap in caplist:
        name = cap.name
        name_cf = name.casefold()
        cap_event = partial(CapEvent, base_event=event, cap=name, cap_param=cap.value)
        tasks = [
            bot.plugin_manager.internal_launch(_hook, cap_event(hook=_hook))
            for _hook in bot.plugin_manager.cap_hooks["on_available"][name_cf]
        ]
        results = yield from asyncio.gather(*tasks)
        if any(ok and (res or res is None) for ok, res in results):
            cap_queue[name_cf] = async_util.create_future(conn.loop)
            conn.cmd("CAP", "REQ", cap)

    if irc_paramlist[2] != '+':
        yield from asyncio.gather(*cap_queue.values())
        cap_queue.clear()
        conn.send("CAP END")


HANDLERS = {}


def _subcmd_handler(*types):
    def _decorate(func):
        for subcmd in types:
            HANDLERS[subcmd.upper()] = func

        return func

    return lambda func: _decorate(func)


@asyncio.coroutine
def _launch_handler(subcmd, event, **kwargs):
    subcmd = subcmd.upper()
    kwargs["subcmd"] = subcmd
    try:
        handler = HANDLERS[subcmd]
    except LookupError:
        return

    yield from async_util.run_func_with_args(event.loop, handler, ChainMap(event, kwargs))


@_subcmd_handler("LS")
@asyncio.coroutine
def cap_ls(conn, caplist, event, irc_paramlist, bot, logger):
    logger.info("[%s|cap] Available capabilities: %s", conn.name, caplist)
    yield from handle_available_caps(conn, caplist, event, irc_paramlist, bot)


@asyncio.coroutine
def handle_req_resp(enabled, conn, caplist, event, bot):
    server_caps = conn.memory.setdefault('server_caps', {})
    cap_queue = conn.memory.get("cap_queue", {})
    caps = (cap.name.casefold() for cap in caplist)
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


@_subcmd_handler("ACK")
@asyncio.coroutine
def cap_ack_nak(conn, caplist, event, bot):
    yield from handle_req_resp(True, conn, caplist, event, bot)


@_subcmd_handler("NAK")
@asyncio.coroutine
def cap_nak(conn, caplist, event, bot):
    yield from handle_req_resp(False, conn, caplist, event, bot)


@_subcmd_handler("LIST")
def cap_list(logger, caplist, conn):
    logger.info("[%s|cap] Enabled Capabilities: %s", conn.name, caplist)


@_subcmd_handler("NEW")
@asyncio.coroutine
def cap_new(logger, caplist, conn, event, bot, irc_paramlist):
    logger.info("[%s|cap] New capabilities advertised: %s", conn.name, caplist)
    yield from handle_available_caps(conn, caplist, event, irc_paramlist, bot)


@_subcmd_handler("DEL")
def cap_del(logger, conn, caplist):
    # TODO add hooks for CAP removal
    logger.info("[%s|cap] Capabilities removed by server: %s", conn.name, caplist)
    server_caps = conn.memory.setdefault('server_caps', {})
    for cap in caplist:
        server_caps[cap.name.casefold()] = False


@hook.irc_raw("CAP")
@asyncio.coroutine
def on_cap(irc_paramlist, event):
    args = {}
    if len(irc_paramlist) > 2:
        capstr = irc_paramlist[-1].strip()
        if capstr[0] == ':':
            capstr = capstr[1:]

        args["caplist"] = CapList.parse(capstr)

    yield from _launch_handler(irc_paramlist[1], event, **args)
