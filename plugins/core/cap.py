import asyncio
from collections import ChainMap
from functools import partial

from cloudbot import hook
from cloudbot.clients.irc.parser import CapList
from cloudbot.event import CapEvent
from cloudbot.util import async_util


class ServerCaps:
    def __init__(self):
        self.available = set()
        self.enabled = set()
        self.request_queue = {}

    def clear(self):
        self.available.clear()
        self.enabled.clear()
        self.request_queue.clear()


def get_caps(conn):
    """
    :type conn: cloudbot.client.Client
    :rtype: ServerCaps
    """
    try:
        return conn.memory["server_caps"]
    except KeyError:
        conn.memory["server_caps"] = caps = ServerCaps()
        return caps


@hook.connect(priority=-10, clients="irc")
def send_cap_ls(conn):
    caps = get_caps(conn)
    if not isinstance(caps, ServerCaps):
        conn.memory["server_caps"] = ServerCaps()

    caps.clear()
    conn.cmd("CAP", "LS", "302")


@asyncio.coroutine
def handle_available_caps(conn, caplist, event, irc_paramlist, bot):
    caps = get_caps(conn)
    available_caps = caps.available
    available_caps.update(caplist)
    cap_queue = caps.request_queue
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
            conn.cmd("CAP", "REQ", cap.name)

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
    if enabled:
        event.logger.info("[%s|cap] Capabilities Acknowledged: %s", conn.name, caplist)
    else:
        event.logger.info("[%s|cap] Capabilities Failed: %s", conn.name, caplist)

    cap_info = get_caps(conn)
    enabled_caps = cap_info.enabled
    caps = ((cap.name.casefold(), cap) for cap in caplist)
    for name, cap in caps:
        if enabled:
            enabled_caps.add(cap)

            cap_event = partial(CapEvent, base_event=event, cap=name, cap_param=cap.value)
            tasks = [
                bot.plugin_manager.launch(_hook, cap_event(hook=_hook))
                for _hook in bot.plugin_manager.cap_hooks["on_ack"][name]
            ]
            yield from asyncio.gather(*tasks)

        try:
            fut = cap_info.request_queue.pop(name)
        except KeyError as e:
            raise KeyError("Got ACK/NAK for CAP not in request queue") from e
        else:
            fut.set_result(enabled)


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
    server_caps = get_caps(conn)
    server_caps.available -= set(caplist)
    server_caps.enabled -= set(caplist)


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
