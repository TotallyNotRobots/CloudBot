import asyncio
import logging
import random
import re
import ssl
from functools import partial

from .parser import Message
from .permissions import IrcPermissionManager
from ...client import Client
from ...event import Event, EventType, IrcOutEvent
from ...util.async_util import wrap_future, create_future

logger = logging.getLogger("cloudbot")

irc_nick_re = re.compile(r'[A-Za-z0-9^{\}\[\]\-`_|\\]+')

irc_bad_chars = ''.join([chr(x) for x in list(range(0, 1)) + list(range(4, 32)) + list(range(127, 160))])
irc_clean_re = re.compile('[{}]'.format(re.escape(irc_bad_chars)))


def irc_clean(dirty):
    return irc_clean_re.sub('', dirty)


irc_command_to_event_type = {
    "PRIVMSG": EventType.message,
    "JOIN": EventType.join,
    "PART": EventType.part,
    "KICK": EventType.kick,
    "NOTICE": EventType.notice
}


def decode(bytestring):
    """
    Tries to decode a bytestring using multiple encoding formats
    """
    for codec in ('utf-8', 'iso-8859-1', 'shift_jis', 'cp1252'):
        try:
            return bytestring.decode(codec)
        except UnicodeDecodeError:
            continue
    # noinspection PyUnreachableCode
    return bytestring.decode('utf-8', errors='ignore')


class IrcClient(Client):
    """
    An implementation of Client for IRC.
    :type use_ssl: bool
    :type server: str
    :type port: int
    :type _ignore_cert_errors: bool
    """

    def __init__(self, bot, name, config):
        """
        :type bot: cloudbot.bot.CloudBot
        :type name: str
        :type config: dict[str, unknown]
        """
        self.use_ssl = config['connection'].get('ssl', False)
        self._ignore_cert_errors = config['connection']['ignore_cert']
        self._timeout = config['connection'].get('timeout', 300)
        self.server = config['connection']['server']
        self.port = config['connection'].get('port', 6667)

        local_bind = (config['connection'].get('bind_addr', False), config['connection'].get('bind_port', 0))
        if local_bind[0] is False:
            local_bind = False

        self.local_bind = local_bind

        # transport and protocol
        self._transport = None
        self._protocol = None

        self._connecting = False

        super().__init__(bot, name, 'irc', config)

    def get_permissions_manager(self):
        return IrcPermissionManager(self)

    def describe_server(self):
        if self.use_ssl:
            return "{}:+{}".format(self.server, self.port)

        return "{}:{}".format(self.server, self.port)

    @asyncio.coroutine
    def auto_reconnect(self):
        """
        This method should be called by code that attempts to automatically reconnect to a server

        This differs from self.try_connect() as it checks whether or not it should automatically reconnect
        before doing so. This is useful for instances where the socket has been closed, an EOF received,
        or a ping timeout occurred.
        """
        if not self._active:
            return

        yield from self.try_connect()

    @asyncio.coroutine
    def try_connect(self):
        while not self.connected:
            try:
                yield from self.connect(self._timeout)
            except (asyncio.TimeoutError, OSError):
                logger.exception("[%s] Error occurred while connecting", self.name)
            else:
                break

            yield from asyncio.sleep(random.randrange(self._timeout))

    @asyncio.coroutine
    def connect(self, timeout=None):
        """
        Connects to the IRC server, or reconnects if already connected.
        """
        if self._connecting:
            raise ValueError("Attempted to connect while another connect attempt is happening")

        self._connecting = True
        try:
            return (yield from self._connect(timeout))
        finally:
            self._connecting = False

    @asyncio.coroutine
    def _connect(self, timeout=None):
        # connect to the clients server
        if self.connected:
            logger.info("[{}] Reconnecting".format(self.name))
            self.quit("Reconnecting...")
        else:
            logger.info("[{}] Connecting".format(self.name))

        self._active = True

        optional_params = {}
        if self.local_bind:
            optional_params["local_addr"] = self.local_bind

        if self.use_ssl:
            ssl_context = ssl.create_default_context()
            if self._ignore_cert_errors:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            optional_params["ssl"] = ssl_context

        coro = self.loop.create_connection(
            partial(_IrcProtocol, self), host=self.server, port=self.port, **optional_params
        )

        if timeout is not None:
            coro = asyncio.wait_for(coro, timeout)

        self._transport, self._protocol = yield from coro

        tasks = [
            self.bot.plugin_manager.launch(hook, Event(bot=self.bot, conn=self, hook=hook))
            for hook in self.bot.plugin_manager.connect_hooks
            if not hook.clients or self.type in hook.clients
        ]
        # TODO stop connecting if a connect hook fails?
        yield from asyncio.gather(*tasks)

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

    def send_nick(self, nick):
        self.cmd("NICK", nick)

    def join(self, channel):
        self.cmd("JOIN", channel)

    def part(self, channel):
        self.cmd("PART", channel)

    def send_pass(self, password):
        if not password:
            return
        self.cmd("PASS", password)

    def ctcp(self, target, ctcp_type, text):
        """
        Makes the bot send a PRIVMSG CTCP of type <ctcp_type> to the target
        :type ctcp_type: str
        :type text: str
        :type target: str
        """
        out = "\x01{} {}\x01".format(ctcp_type, text)
        self.cmd("PRIVMSG", target, out)

    def cmd(self, command, *params):
        """
        Sends a raw IRC command of type <command> with params <params>
        :param command: The IRC command to send
        :param params: The params to the IRC command
        :type command: str
        :type params: (str)
        """
        params = list(map(str, params))  # turn the tuple of parameters into a list
        if params:
            params[-1] = ':' + params[-1]
            self.send("{} {}".format(command, ' '.join(params)))
        else:
            self.send(command)

    def send(self, line, log=True):
        """
        Sends a raw IRC line
        :type line: str
        :type log: bool
        """
        if not self.connected:
            raise ValueError("Client must be connected to irc server to use send")
        self.loop.call_soon_threadsafe(self._send, line, log)

    def _send(self, line, log=True):
        """
        Sends a raw IRC line unchecked. Doesn't do connected check, and is *not* threadsafe
        :type line: str
        :type log: bool
        """
        wrap_future(self._protocol.send(line, log=log), loop=self.loop)

    @property
    def connected(self):
        return self._protocol and self._protocol.connected

    def is_nick_valid(self, nick):
        return bool(irc_nick_re.fullmatch(nick))

    def is_channel(self, name):
        return name and name[0] in "&#!+.~" and ' ' not in name


class _IrcProtocol(asyncio.Protocol):
    """
    :type loop: asyncio.events.AbstractEventLoop
    :type conn: IrcClient
    :type bot: cloudbot.bot.CloudBot
    :type _input_buffer: bytes
    :type _connected: bool
    :type _transport: asyncio.transports.Transport
    :type _connected_future: asyncio.Future
    """

    def __init__(self, conn):
        """
        :type conn: IrcClient
        """
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
        self._connected_future = create_future(self.loop)

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
            logger.error("[{}] Connection lost: {}".format(self.conn.name, exc))

        wrap_future(self.conn.auto_reconnect(), loop=self.loop)

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

    @asyncio.coroutine
    def send(self, line, log=True):
        # make sure we are connected before sending
        if not self.connected:
            if self._connecting:
                yield from self._connected_future
            else:
                raise ValueError("Attempted to send data to a closed connection")

        old_line = line
        filtered = bool(self.bot.plugin_manager.out_sieves)

        for out_sieve in self.bot.plugin_manager.out_sieves:
            event = IrcOutEvent(
                bot=self.bot, hook=out_sieve, conn=self.conn, irc_raw=line
            )

            ok, new_line = yield from self.bot.plugin_manager.internal_launch(out_sieve, event)
            if not ok:
                logger.warning("Error occurred in outgoing sieve, falling back to old behavior")
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
            logger.info("[{}|out] >> {!r}".format(self.conn.name, line))

        self._transport.write(line)

    def data_received(self, data):
        self._input_buffer += data

        while b"\r\n" in self._input_buffer:
            line_data, self._input_buffer = self._input_buffer.split(b"\r\n", 1)
            line = decode(line_data)

            try:
                message = Message.parse(line)
            except Exception:
                logger.exception(
                    "[%s] Error occurred while parsing IRC line '%s' from %s",
                    self.conn.name, line, self.conn.describe_server()
                )
                continue

            command = message.command
            command_params = message.parameters

            # Reply to pings immediately

            if command == "PING":
                self.conn.send("PONG " + command_params[-1], log=False)

            # Parse the command and params

            # Content
            if command_params.has_trail:
                content_raw = command_params[-1]
                content = irc_clean(content_raw)
            else:
                content_raw = None
                content = None

            # Event type
            if command in irc_command_to_event_type:
                event_type = irc_command_to_event_type[command]
            else:
                event_type = EventType.other

            # Target (for KICK, INVITE)
            if event_type is EventType.kick:
                target = command_params[1]
            elif command == "INVITE":
                target = command_params[0]
            else:
                # TODO: Find more commands which give a target
                target = None

            # Parse for CTCP
            if event_type is EventType.message and content_raw.count("\x01") >= 2 and content_raw.startswith("\x01"):
                # Remove the first \x01, then rsplit to remove the last one, and ignore text after the last \x01
                ctcp_text = content_raw[1:].rsplit("\x01", 1)[0]
                ctcp_text_split = ctcp_text.split(None, 1)
                if ctcp_text_split[0] == "ACTION":
                    # this is a CTCP ACTION, set event_type and content accordingly
                    event_type = EventType.action
                    content = ctcp_text_split[1]
                else:
                    # this shouldn't be considered a regular message
                    event_type = EventType.other
            else:
                ctcp_text = None

            # Channel
            channel = None
            if command_params:
                if command in ["NOTICE", "PRIVMSG", "KICK", "JOIN", "PART", "MODE"]:
                    channel = command_params[0]
                elif command == "INVITE":
                    channel = command_params[1]
                elif len(command_params) > 2 or not (command_params.has_trail and len(command_params) == 1):
                    channel = command_params[0]

            prefix = message.prefix

            nick = prefix.nick
            user = prefix.user
            host = prefix.host
            mask = prefix.mask

            if channel:
                # TODO Migrate plugins to accept the original case of the channel
                channel = channel.lower()

                channel = channel.split()[0]  # Just in case there is more data

                if channel == self.conn.nick.lower():
                    channel = nick.lower()

            # Set up parsed message
            # TODO: Do we really want to send the raw `prefix` and `command_params` here?
            event = Event(
                bot=self.bot, conn=self.conn, event_type=event_type, content_raw=content_raw, content=content,
                target=target, channel=channel, nick=nick, user=user, host=host, mask=mask, irc_raw=line,
                irc_prefix=mask, irc_command=command, irc_paramlist=command_params, irc_ctcp_text=ctcp_text
            )

            self.bot.event_queue.put_nowait(event)

    @property
    def connected(self):
        return self._connected
