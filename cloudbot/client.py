import asyncio
import collections
import logging
import random

from .permissions import NickBasedPermissionManager

logger = logging.getLogger("cloudbot")


class Client:
    """
    A Client representing each connection the bot makes to a single server
    :type bot: cloudbot.bot.CloudBot
    :type loop: asyncio.events.AbstractEventLoop
    :type name: str
    :type config: dict[str, unknown]
    :type nick: str
    :type channels: list[str]
    :type config_channels: list[str]
    :type vars: dict
    :type history: dict[str, list[tuple]]
    :type permissions: cloudbot.permissions.AbstractPermissionManager
    :type memory: dict
    :type ready: bool
    """

    def __init__(self, bot, name, client_type, config):
        """
        :type bot: cloudbot.bot.CloudBot
        :type name: str
        :type client_type: str
        :type config: dict[str, unknown]
        """
        self.bot = bot
        self.loop = bot.loop
        self.name = name
        self._type = client_type
        self.config = config

        self.nick = None

        self.channels = []
        self.config_channels = []

        self.vars = {}
        self.history = {}

        # create permissions manager
        self.permissions = self.get_permissions_manager()

        # for plugins to abuse
        self.memory = collections.defaultdict()

        # set when on_load in core_misc is done
        self.ready = False

        self._active = False

        self.reload_config()

    def reload_config(self):
        nick = self.config['nick']
        if nick != self.nick:
            self.set_nick(nick)

        channels = self.config['channels']
        if channels != self.config_channels and self.connected:
            for chan in channels:
                if chan not in self.config_channels:
                    self.join(chan)

            for chan in self.config_channels:
                if chan not in channels:
                    self.part(chan)

        self.config_channels = channels

        self.permissions.reload()

    def get_permissions_manager(self):
        return NickBasedPermissionManager(self)

    def describe_server(self):
        raise NotImplementedError

    @asyncio.coroutine
    def auto_reconnect(self):
        if not self._active:
            return

        yield from self.try_connect()

    @asyncio.coroutine
    def try_connect(self):
        timeout = 30
        while not self.connected:
            try:
                yield from self.connect(timeout)
            except Exception:
                logger.exception("[%s] Error occurred while connecting.", self.name)
            else:
                break

            yield from asyncio.sleep(random.randrange(timeout))

    @asyncio.coroutine
    def connect(self, timeout=None):
        """
        Connects to the server, or reconnects if already connected.
        """
        raise NotImplementedError

    def quit(self, reason=None, set_inactive=True):
        """
        Gracefully disconnects from the server with reason <reason>, close() should be called shortly after.
        """
        raise NotImplementedError

    def close(self):
        """
        Disconnects from the server, only for use when this Client object will *not* ever be connected again
        """
        raise NotImplementedError

    def message(self, target, *text):
        """
        Sends a message to the given target
        :type target: str
        :type text: str
        """
        raise NotImplementedError

    def admin_log(self, text, console=True):
        """
        Log a message to the configured admin channel
        :type text: str
        :type console: bool
        """
        raise NotImplementedError

    def action(self, target, text):
        """
        Sends an action (or /me) to the given target channel
        :type target: str
        :type text: str
        """
        raise NotImplementedError

    def notice(self, target, text):
        """
        Sends a notice to the given target
        :type target: str
        :type text: str
        """
        raise NotImplementedError

    def set_nick(self, nick):
        """
        Sets the bot's nickname
        :type nick: str
        """
        if self.connected:
            self.send_nick(nick)
        else:
            self.nick = nick

    def send_nick(self, nick):
        """
        Send the nick change request to the server
        :type nick: str
        """
        raise NotImplementedError

    def join(self, channel):
        """
        Joins a given channel
        :type channel: str
        """
        raise NotImplementedError

    def part(self, channel):
        """
        Parts a given channel
        :type channel: str
        """
        raise NotImplementedError

    def is_nick_valid(self, nick):
        """
        Determines if a nick is valid for this connection
        :param nick: The nick to check
        :return: True if it is valid, otherwise false
        """
        raise NotImplementedError

    def is_channel(self, name):
        """
        Determines if a name represents a valid channel for this connection or not
        :type name: str
        :param name: The name to check
        :rtype: bool
        :return: True if the channel is valid, False otherwise
        """
        raise NotImplementedError

    @property
    def connected(self):
        raise NotImplementedError

    @property
    def type(self):
        return self._type

    @property
    def active(self):
        return self._active
