from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from cloudbot import hook

if TYPE_CHECKING:
    from cloudbot.client import Client
    from cloudbot.clients.irc import IrcClient

logger = logging.getLogger("cloudbot")


@hook.on_cap_available("sasl")
def sasl_available(conn: Client):
    sasl_conf = conn.config.get("sasl")
    return bool(sasl_conf and sasl_conf.get("enabled", True))  # pyright: ignore[reportAny] # TODO: type config


@hook.on_cap_ack("sasl")
async def sasl_ack(conn: IrcClient) -> None:
    sasl_auth = conn.config.get("sasl")
    if sasl_auth and sasl_auth.get("enabled", True):  # pyright: ignore[reportAny] # TODO: type config
        sasl_mech = sasl_auth.get("mechanism", "PLAIN").upper()  # pyright: ignore[reportAny] # TODO: type config
        auth_fut = conn.loop.create_future()
        conn.memory["sasl_auth_future"] = auth_fut
        conn.cmd("AUTHENTICATE", sasl_mech)  # pyright: ignore[reportAny] # TODO: type config
        cmd, arg = await auth_fut
        if cmd == "908":
            logger.warning("[%s|sasl] SASL mechanism not supported", conn.name)
        elif cmd == "AUTHENTICATE" and arg[0] == "+":
            num_fut = conn.loop.create_future()
            conn.memory["sasl_numeric_future"] = num_fut
            if sasl_mech == "PLAIN":
                auth_str = f"{sasl_auth['user']}\x00{sasl_auth['user']}\x00{sasl_auth['pass']}".encode()
                conn.cmd("AUTHENTICATE", base64.b64encode(auth_str).decode())
            else:
                conn.cmd("AUTHENTICATE", "+")
            numeric = await num_fut
            if numeric == "902":
                logger.warning("[%s|sasl] SASL nick locked", conn.name)
            elif numeric == "903":
                logger.info("[%s|sasl] SASL auth successful", conn.name)
            elif numeric == "904":
                logger.warning("[%s|sasl] SASL auth failed", conn.name)
            elif numeric == "905":
                logger.warning("[%s|sasl] SASL auth too long", conn.name)
            elif numeric == "906":
                logger.warning("[%s|sasl] SASL auth aborted", conn.name)
            elif numeric == "907":
                logger.warning(
                    "[%s|sasl] SASL auth already completed", conn.name
                )


@hook.irc_raw(["AUTHENTICATE", "908"])
async def auth(irc_command, conn: Client, irc_paramlist) -> None:
    future = conn.memory.get("sasl_auth_future")
    if future and not future.done():
        future.set_result((irc_command, irc_paramlist))


@hook.irc_raw(["902", "903", "904", "905", "906", "907"])
async def sasl_numerics(irc_command, conn: Client) -> None:
    future = conn.memory.get("sasl_numeric_future")
    if future and not future.done():
        future.set_result(irc_command)
