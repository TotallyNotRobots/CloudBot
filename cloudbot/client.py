import asyncio
import collections
import logging
import random

from cloudbot.permissions import PermissionManager

logger = logging.getLogger("cloudbot")

CLIENTS = {}


def client(_type):
    def _decorate(cls):
        CLIENTS[_type] = cls
        cls._type = _type
        return cls

    return lambda cls: _decorate(cls)


class Client:
    """
    A Client representing each connection the bot makes to a single server
    :type bot: cloudbot.bot.CloudBot
    :type loop: asyncio.events.AbstractEventLoop
    :type name: str
    :type channels: list[str]
    :type config: dict[str, unknown]
    :type nick: str
    :type vars: dict
    :type history: dict[str, list[tuple]]
    :type permissions: PermissionManager
    """

    _type = None

    def __init__(self, bot, name, nick, *, channels=None, config=None):
        """
        :type bot: cloudbot.bot.CloudBot
        :type name: str
        :type nick: str
        :type channels: list[str]
        :type config: dict[str, unknown]
        """
        self.bot = bot
        self.loop = bot.loop
        self.name = name
        self.nick = nick

        if channels is None:
            self.channels = []
        else:
            self.channels = channels

        if config is None:
            self.config = {}
        else:
            self.config = config
        self.vars = {}
        self.history = {}

        # create permissions manager
        self.permissions = PermissionManager(self)

        # for plugins to abuse
        self.memory = collections.defaultdict()

        # set when on_load in core_misc is done
        self.ready = False

        self._active = False

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

    def quit(self, reason=None):
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

    @property
    def connected(self):
        raise NotImplementedError

    @property
    def type(self):
        return self._type

    @property
    def active(self):
        return self._active
