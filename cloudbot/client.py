from __future__ import annotations

import asyncio
import logging
import random
from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any

from cloudbot.permissions import PermissionManager
from cloudbot.util import CLIENT_ATTR
from cloudbot.util.extensible_data import Extensible

if TYPE_CHECKING:
    from cloudbot.bot import AbstractBot

logger = logging.getLogger("cloudbot")


def client(_type):
    def _decorate(cls):
        setattr(cls, CLIENT_ATTR, _type)
        return cls

    return _decorate


class ClientConnectError(Exception):
    def __init__(self, client_name, server) -> None:
        super().__init__(
            f"Unable to connect to client {client_name} with server {server}"
        )
        self.client_name = client_name
        self.server = server


class Client(Extensible):
    """
    A Client representing each connection the bot makes to a single server
    """

    def __init__(
        self,
        bot: AbstractBot,
        _type: str,
        name: str,
        nick: str,
        *,
        channels=None,
        config=None,
    ) -> None:
        super().__init__()
        self.bot = bot
        if bot.loop is None:
            raise ValueError("Missing event loop on bot")

        self.loop = bot.loop
        self.name = name
        self.nick = nick
        self._type = _type

        self.channels = list[str]()

        if channels is None:
            self.config_channels = []
        else:
            self.config_channels = channels

        if config is None:
            self.config = {}
        else:
            self.config = config

        self.vars = dict[str, Any]()
        self.history = defaultdict[str, deque[tuple[str, float, str]]](
            lambda: deque[tuple[str, float, str]](maxlen=100)
        )

        # create permissions manager
        self.permissions = PermissionManager(self)

        # for plugins to abuse
        self.memory = defaultdict[str, Any]()

        # set when on_load in core_misc is done
        self.ready = False

        self._active = False

        self.cancelled_future = self.loop.create_future()

    def describe_server(self):
        raise NotImplementedError

    async def auto_reconnect(self) -> None:
        if not self._active:
            return

        await self.try_connect()

    async def try_connect(self) -> None:
        timeout = 30
        while self.active and not self.connected:
            try:
                await self.connect(timeout)
            except Exception:
                logger.exception(
                    "[%s] Error occurred while connecting.", self.name
                )
            else:
                break

            await asyncio.sleep(random.randrange(timeout))

    async def connect(self, timeout=None):
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
        """
        raise NotImplementedError

    def admin_log(self, text, console=True):
        """
        Log a message to the configured admin channel
        """
        raise NotImplementedError

    def action(self, target, text):
        """
        Sends an action (or /me) to the given target channel
        """
        raise NotImplementedError

    def notice(self, target, text):
        """
        Sends a notice to the given target
        """
        raise NotImplementedError

    def set_nick(self, nick):
        """
        Sets the bot's nickname
        """
        raise NotImplementedError

    def join(self, channel, key=None):
        """
        Joins a given channel
        """
        raise NotImplementedError

    def part(self, channel):
        """
        Parts a given channel
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

    @active.setter
    def active(self, value) -> None:
        self._active = value

    def reload(self) -> None:
        self.permissions.reload()
