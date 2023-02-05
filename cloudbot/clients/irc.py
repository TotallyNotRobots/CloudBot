import asyncio
import logging
import random
import re
import socket
import ssl
import traceback
from functools import partial
from itertools import chain
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple, Union, cast

from irclib.parser import Message

from cloudbot.client import Client, ClientConnectError, client
from cloudbot.event import Event, EventType, IrcOutEvent
from cloudbot.util import async_util, colors

logger = logging.getLogger("cloudbot")

irc_nick_re = re.compile(r"[A-Za-z0-9^{}\[\]\-`_|\\]+")

irc_bad_chars = "".join(
    (
        c
        for c in (chr(x) for x in chain(range(0, 32), range(127, 160)))
        if c not in colors.IRC_FORMATTING_DICT.values() and c != "\1"
    )
)

irc_clean_re = re.compile("[{}]".format(re.escape(irc_bad_chars)))


def irc_clean(dirty: str) -> str:
    return irc_clean_re.sub("", dirty)


irc_command_to_event_type = {
    "PRIVMSG": EventType.message,
    "JOIN": EventType.join,
    "PART": EventType.part,
    "KICK": EventType.kick,
    "NOTICE": EventType.notice,
}

content_params = {
    "PRIVMSG": 1,
    "NOTICE": 1,
    "PART": 1,
    "KICK": 2,
    "TOPIC": 1,
    "NICK": 0,
    "QUIT": 0,
}

chan_params = {
    "PRIVMSG": 0,
    "NOTICE": 0,
    "JOIN": 0,
    "PART": 0,
    "TOPIC": 0,
    "MODE": 0,
    "KICK": 0,
    "INVITE": 1,
    "353": 2,
    "366": 1,
    "324": 1,
    "329": 1,
    "332": 1,
    "333": 1,
    # WHOIS
    "310": 1,
    "311": 1,
    "312": 1,
    "318": 1,
}

target_params = {
    "KICK": 1,
    "INVITE": 0,
    "MODE": 0,
}


def decode(bytestring):
    """
    Tries to decode a bytestring using multiple encoding formats

    >>> decode(bytes([0x80, 0xbf, 0x81]) + '\u200b'.encode())
    '\u200b'
    """
    for codec in ("utf-8", "shift_jis", "cp1252"):
        try:
            return bytestring.decode(codec)
        except UnicodeDecodeError:
            continue

    return bytestring.decode("utf-8", errors="ignore")


def _get_param(msg: Message, index_map: Mapping[str, int]) -> Optional[str]:
    if msg.command in index_map:
        idx = index_map[msg.command]
        if idx < len(msg.parameters):
            return cast(str, msg.parameters[idx])

    return None


@client("irc")
class IrcClient(Client):
    """
    An implementation of Client for IRC.
    """

    def __init__(self, bot, _type, name, nick, *, channels=None, config=None):
        """ """
        super().__init__(
            bot, _type, name, nick, channels=channels, config=config
        )

        self.target_nick = nick
        conn_config = config["connection"]
        self.use_ssl = conn_config.get("ssl", False)
        self._ignore_cert_errors = conn_config.get("ignore_cert", False)
        self._timeout = conn_config.get("timeout", 300)
        self.server = conn_config["server"]
        self.port = conn_config.get("port", 6667)

        local_bind = (
            conn_config.get("bind_addr"),
            conn_config.get("bind_port"),
        )

        self.local_bind: Union[bool, Tuple[str, str]]
        if not (local_bind[0] or local_bind[1]):
            self.local_bind = False
        else:
            self.local_bind = local_bind

        # create SSL context
        self.ssl_context = self.make_ssl_context(conn_config)

        # transport and protocol
        self._transport = None
        self._protocol = None

        self._connecting = False

        self._channel_keys: Dict[str, str] = {}

    def set_channel_key(
        self, channel: str, key: str, *, override: bool = True
    ) -> None:
        if override or channel not in self._channel_keys:
            self._channel_keys[channel] = key

    def clear_channel_keys(self) -> None:
        self._channel_keys.clear()

    def clear_channel_key(self, channel: str) -> bool:
        if channel in self._channel_keys:
            del self._channel_keys[channel]
            return True

        return False

    def get_channel_key(
        self,
        channel: str,
        default: Optional[str] = None,
        *,
        set_key: bool = True,
    ) -> Optional[str]:
        if channel in self._channel_keys:
            key = self._channel_keys[channel]
            if key is not None:
                return key

        if set_key:
            self._channel_keys[channel] = default

        return default

    def make_ssl_context(self, conn_config):
        if self.use_ssl:
            ssl_context = ssl.create_default_context()
            client_cert = conn_config.get("client_cert")
            if client_cert:
                path = Path(client_cert)
                if path.exists():
                    ssl_context.load_cert_chain(str(path.resolve()))
                else:
                    logger.warning("[%s] Unable to load client cert", self.name)

            if self._ignore_cert_errors:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                ssl_context.verify_mode = ssl.CERT_REQUIRED
        else:
            ssl_context = None

        return ssl_context

    def describe_server(self):
        if self.use_ssl:
            return "+{}:{}".format(self.server, self.port)

        return "{}:{}".format(self.server, self.port)

    async def auto_reconnect(self):
        """
        This method should be called by code that attempts to automatically reconnect to a server

        This differs from self.try_connect() as it checks whether or not it should automatically reconnect
        before doing so. This is useful for instances where the socket has been closed, an EOF received,
        or a ping timeout occurred.
        """
        if not self._active:
            return

        await self.try_connect()

    async def try_connect(self):
        while self.active and not self.connected:
            try:
                await self.connect(self._timeout)
            except (TimeoutError, asyncio.TimeoutError):
                logger.error(
                    "[%s] Timeout occurred while connecting to %s",
                    self.name,
                    self.describe_server(),
                )
            except (socket.error, socket.gaierror, OSError, ssl.SSLError):
                logger.error(
                    "[%s] Error occurred while connecting to %s (%s)",
                    self.name,
                    self.describe_server(),
                    traceback.format_exc().splitlines()[-1],
                )
            except Exception as e:
                raise ClientConnectError(
                    self.name, self.describe_server()
                ) from e
            else:
                break

            sleep_time = random.randrange(self._timeout)
            canceller = asyncio.shield(self.cancelled_future)
            try:
                await asyncio.wait_for(canceller, timeout=sleep_time)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    async def connect(self, timeout=None):
        """
        Connects to the IRC server, or reconnects if already connected.
        """
        if self._connecting:
            raise ValueError(
                "Attempted to connect while another connect attempt is happening"
            )

        self._connecting = True
        try:
            return await self._connect(timeout)
        finally:
            self._connecting = False

    async def _connect(self, timeout=None):
        # connect to the clients server
        if self.connected:
            logger.info("[%s] Reconnecting", self.name)
            self.quit("Reconnecting...")
        else:
            logger.info("[%s] Connecting", self.name)

        self._active = True

        optional_params = {}
        if self.local_bind:
            optional_params["local_addr"] = self.local_bind

        coro = self.loop.create_connection(
            partial(_IrcProtocol, self),
            host=self.server,
            port=self.port,
            ssl=self.ssl_context,
            **optional_params,
        )

        if timeout is not None:
            coro = asyncio.wait_for(coro, timeout)

        self._transport, self._protocol = await coro

        tasks = [
            self.bot.plugin_manager.launch(
                hook, Event(bot=self.bot, conn=self, hook=hook)
            )
            for hook in self.bot.plugin_manager.connect_hooks
            if not hook.clients or self.type in hook.clients
        ]
        # TODO stop connecting if a connect hook fails?
        await asyncio.gather(*tasks)

    def quit(self, reason=None, set_inactive=True):
        if set_inactive:
            self._active = False

        if self.connected:
            if reason:
                self.cmd("QUIT", reason)
            else:
                self.cmd("QUIT")

    def close(self):
        self.quit()
        if self._protocol:
            self._protocol.close()

    def message(self, target, *messages):
        for text in messages:
            self.cmd("PRIVMSG", target, text)

    def admin_log(self, text, console=True):
        log_chan = self.config.get("log_channel")
        if log_chan:
            self.message(log_chan, text)

        if console:
            logger.info("[%s|admin] %s", self.name, text)

    def action(self, target, text):
        self.ctcp(target, "ACTION", text)

    def notice(self, target, text):
        self.cmd("NOTICE", target, text)

    def set_nick(self, nick):
        self.cmd("NICK", nick)

    def join(self, channel, key=None):
        key = self.get_channel_key(channel, key)
        if key:
            self.cmd("JOIN", channel, key)
        else:
            self.cmd("JOIN", channel)

        if channel not in self.channels:
            self.channels.append(channel)

    def part(self, channel):
        self.cmd("PART", channel)
        if channel in self.channels:
            self.channels.remove(channel)

    def set_pass(self, password):
        if not password:
            return
        self.cmd("PASS", password)

    def ctcp(self, target, ctcp_type, text):
        """
        Makes the bot send a PRIVMSG CTCP of type <ctcp_type> to the target
        """
        out = "\x01{} {}\x01".format(ctcp_type, text)
        self.cmd("PRIVMSG", target, out)

    def cmd(self, command, *params):
        """
        Sends a raw IRC command of type <command> with params <params>
        :param command: The IRC command to send
        :param params: The params to the IRC command
        """
        # turn the tuple of parameters into a list
        param_list = list(map(str, params))
        self.send(str(Message(None, None, command, param_list)))

    def send(self, line, log=True):
        """
        Sends a raw IRC line
        """
        if not self.connected:
            raise ValueError(
                "Client must be connected to irc server to use send"
            )

        self.loop.call_soon_threadsafe(self._send, line, log)

    def _send(self, line, log=True):
        """
        Sends a raw IRC line unchecked. Doesn't do connected check, and is *not* threadsafe
        """
        async_util.wrap_future(
            self._protocol.send(line, log=log), loop=self.loop
        )

    @property
    def connected(self):
        return self._protocol and self._protocol.connected

    def is_nick_valid(self, nick):
        return bool(irc_nick_re.fullmatch(nick))


class _IrcProtocol(asyncio.Protocol):
    """ """

    def __init__(self, conn):
        """ """
        self.loop = conn.loop
        self.bot = conn.bot
        self.conn = conn

        # input buffer
        self._input_buffer = b""

        # connected
        self._connected = False
        self._connecting = True

        # transport
        self._transport = None

        # Future that waits until we are connected
        self._connected_future = async_util.create_future(self.loop)

    def connection_made(self, transport):
        self._transport = transport
        self._connecting = False
        self._connected = True
        self._connected_future.set_result(None)
        # we don't need the _connected_future, everything uses it will check _connected first.
        del self._connected_future

    def connection_lost(self, exc):
        self._connected = False
        if exc:
            logger.error("[%s] Connection lost: %s", self.conn.name, exc)

        async_util.wrap_future(self.conn.auto_reconnect(), loop=self.loop)

    def close(self):
        self._connecting = False
        self._connected = False
        if self._transport:
            self._transport.close()

        try:
            fut = self._connected_future
        except AttributeError:
            pass
        else:
            if not fut.done():
                fut.cancel()

    async def send(self, line, log=True):
        # make sure we are connected before sending
        if not self.connected:
            if self._connecting:
                await self._connected_future
            else:
                raise ValueError(
                    "Attempted to send data to a closed connection"
                )

        old_line = line
        filtered = bool(self.bot.plugin_manager.out_sieves)

        for out_sieve in self.bot.plugin_manager.out_sieves:
            event = IrcOutEvent(
                bot=self.bot, hook=out_sieve, conn=self.conn, irc_raw=line
            )

            ok, new_line = await self.bot.plugin_manager.internal_launch(
                out_sieve, event
            )
            if not ok:
                logger.warning(
                    "Error occurred in outgoing sieve, falling back to old behavior"
                )
                logger.debug("Line was: %s", line)
                filtered = False
                break

            line = new_line
            if line is not None and not isinstance(line, bytes):
                line = str(line)

            if not line:
                return

        if not filtered:
            # No outgoing sieves loaded or one of the sieves errored, fall back to old behavior
            line = old_line[:510] + "\r\n"
            line = line.encode("utf-8", "replace")

        if not isinstance(line, bytes):
            # the line must be encoded before we send it, one of the sieves didn't encode it, fall back to the default
            line = line.encode("utf-8", "replace")

        if log:
            logger.debug("[%s|out] >> %r", self.conn.name, line)

        self._transport.write(line)

    def data_received(self, data):
        self._input_buffer += data

        while b"\r\n" in self._input_buffer:
            line_data, self._input_buffer = self._input_buffer.split(b"\r\n", 1)
            line = decode(line_data)

            try:
                event = self.parse_line(line)
            except Exception:
                logger.exception(
                    "[%s] Error occurred while parsing IRC line '%s' from %s",
                    self.conn.name,
                    line,
                    self.conn.describe_server(),
                )
            else:
                # handle the message, async
                async_util.wrap_future(self.bot.process(event), loop=self.loop)

    def parse_line(self, line: str) -> Event:
        message = Message.parse(line)
        command = message.command
        command_params = message.parameters

        # Reply to pings immediately
        if command == "PING":
            self.conn.send("PONG " + command_params[-1], log=False)

        # Parse the command and params
        # Content
        content_raw = _get_param(message, content_params)
        if content_raw is not None:
            content = irc_clean(content_raw)
        else:
            content = None

        # Event type
        event_type = irc_command_to_event_type.get(command, EventType.other)
        target = _get_param(message, target_params)

        # Parse for CTCP
        if event_type is EventType.message and content_raw.startswith("\x01"):
            possible_ctcp = content_raw[1:]
            if content_raw.endswith("\x01"):
                possible_ctcp = possible_ctcp[:-1]

            if "\x01" in possible_ctcp:
                logger.debug(
                    "[%s] Invalid CTCP message received, "
                    "treating it as a mornal message",
                    self.conn.name,
                )
                ctcp_text = None
            else:
                ctcp_text = possible_ctcp
                ctcp_text_split = ctcp_text.split(None, 1)
                if ctcp_text_split[0] == "ACTION":
                    # this is a CTCP ACTION, set event_type and content accordingly
                    event_type = EventType.action
                    content = irc_clean(ctcp_text_split[1])
                else:
                    # this shouldn't be considered a regular message
                    event_type = EventType.other
        else:
            ctcp_text = None

        # Channel
        channel = _get_param(message, chan_params)

        prefix = message.prefix
        if prefix is None:
            nick = None
            user = None
            host = None
            mask = None
        else:
            nick = prefix.nick
            user = prefix.user
            host = prefix.host
            mask = prefix.mask

        if channel:
            # TODO Migrate plugins to accept the original case of the channel
            channel = channel.lower()

            channel = channel.split()[0]  # Just in case there is more data

            # Channel for a PM is the sending user
            if channel == self.conn.nick.lower():
                channel = nick.lower()
        else:
            # If the channel isn't set, it's the sending user/server
            channel = nick.lower() if nick else nick

        # Set up parsed message
        # TODO: Do we really want to send the raw `prefix` and `command_params` here?
        event = Event(
            bot=self.bot,
            conn=self.conn,
            event_type=event_type,
            content_raw=content_raw,
            content=content,
            target=target,
            channel=channel,
            nick=nick,
            user=user,
            host=host,
            mask=mask,
            irc_raw=line,
            irc_prefix=mask,
            irc_command=command,
            irc_paramlist=command_params,
            irc_ctcp_text=ctcp_text,
            irc_tags=message.tags,
        )
        return event

    @property
    def connected(self):
        return self._connected
