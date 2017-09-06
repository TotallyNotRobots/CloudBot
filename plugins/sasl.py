import asyncio
import base64
import logging

from cloudbot import hook

logger = logging.getLogger("cloudbot")


@hook.on_cap_available("sasl")
def sasl_available():
    pass


@asyncio.coroutine
@hook.on_cap_ack("sasl")
def sasl_ack(conn):
    sasl_auth = conn.config.get('sasl')
    if sasl_auth:
        sasl_mech = sasl_auth.get("mechanism", "PLAIN").upper()
        auth_fut = conn.loop.create_future()
        conn.memory["sasl_auth_future"] = auth_fut
        conn.cmd("AUTHENTICATE", sasl_mech)
        cmd, arg = yield from auth_fut
        if cmd == "908":
            logger.warning("[%s|sasl] SASL mechanism not supported", conn.name)
        elif cmd == "AUTHENTICATE" and arg[0] == '+':
            num_fut = conn.loop.create_future()
            conn.memory["sasl_numeric_future"] = num_fut
            if sasl_mech == "PLAIN":
                auth_str = "{nick}\0{user}\0{passwd}".format(
                    nick=conn.nick, user=sasl_auth["user"], passwd=sasl_auth["pass"]
                ).encode()
                conn.cmd("AUTHENTICATE", base64.b64encode(auth_str).decode())
            else:
                conn.cmd("AUTHENTICATE", '+')
            numeric = yield from num_fut
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


@asyncio.coroutine
@hook.irc_raw(["AUTHENTICATE", "908"])
def auth(irc_command, conn, irc_paramlist):
    future = conn.memory.get("sasl_auth_future")
    if future and not future.done():
        future.set_result((irc_command, irc_paramlist))


@asyncio.coroutine
@hook.irc_raw(["902", "903", "904", "905", "906", "907"])
def sasl_numerics(irc_command, conn):
    future = conn.memory.get("sasl_numeric_future")
    if future and not future.done():
        future.set_result(irc_command)
