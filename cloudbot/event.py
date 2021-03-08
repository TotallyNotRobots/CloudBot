import concurrent.futures
import enum
import logging
from functools import partial
from typing import Any, Iterator, Mapping

from irclib.parser import Message

from cloudbot.util.database import Session

logger = logging.getLogger("cloudbot")


@enum.unique
class EventType(enum.Enum):
    message = 0
    action = 1
    # TODO: Do we actually want to have a 'notice' event type? Should the NOTICE command be a 'message' type?
    notice = 2
    join = 3
    part = 4
    kick = 5
    other = 6


class Event(Mapping[str, Any]):
    def __init__(
        self,
        *,
        bot=None,
        hook=None,
        conn=None,
        base_event=None,
        event_type=EventType.other,
        content=None,
        content_raw=None,
        target=None,
        channel=None,
        nick=None,
        user=None,
        host=None,
        mask=None,
        irc_raw=None,
        irc_prefix=None,
        irc_command=None,
        irc_paramlist=None,
        irc_ctcp_text=None,
        irc_tags=None,
    ):
        """
        All of these parameters except for `bot` and `hook` are optional.
        The irc_* parameters should only be specified for IRC events.

        Note that the `bot` argument may be left out if you specify a `base_event`.

        :param bot: The CloudBot instance this event was triggered from
        :param conn: The Client instance this event was triggered from
        :param hook: The hook this event will be passed to
        :param base_event: The base event that this event is based on. If this parameter is not None, then nick, user,
                            host, mask, and irc_* arguments are ignored
        :param event_type: The type of the event
        :param content: The content of the message, or the reason for an join or part
        :param target: The target of the action, for example the user being kicked, or invited
        :param channel: The channel that this action took place in
        :param nick: The nickname of the sender that triggered this event
        :param user: The user of the sender that triggered this event
        :param host: The host of the sender that triggered this event
        :param mask: The mask of the sender that triggered this event (nick!user@host)
        :param irc_raw: The raw IRC line
        :param irc_prefix: The raw IRC prefix
        :param irc_command: The IRC command
        :param irc_paramlist: The list of params for the IRC command. If the last param is a content param, the ':'
                                should be removed from the front.
        :param irc_ctcp_text: CTCP text if this message is a CTCP command
        """
        self.db = None
        self.db_executor = None
        self.bot = bot
        self.conn = conn
        self.hook = hook
        if base_event is not None:
            # We're copying an event, so inherit values
            if self.bot is None and base_event.bot is not None:
                self.bot = base_event.bot
            if self.conn is None and base_event.conn is not None:
                self.conn = base_event.conn
            if self.hook is None and base_event.hook is not None:
                self.hook = base_event.hook

            # If base_event is provided, don't check these parameters, just inherit
            self.type = base_event.type
            self.content = base_event.content
            self.content_raw = base_event.content_raw
            self.target = base_event.target
            self.chan = base_event.chan
            self.nick = base_event.nick
            self.user = base_event.user
            self.host = base_event.host
            self.mask = base_event.mask
            # clients-specific parameters
            self.irc_raw = base_event.irc_raw
            self.irc_tags = base_event.irc_tags
            self.irc_prefix = base_event.irc_prefix
            self.irc_command = base_event.irc_command
            self.irc_paramlist = base_event.irc_paramlist
            self.irc_ctcp_text = base_event.irc_ctcp_text
        else:
            # Since base_event wasn't provided, we can take these parameters
            self.type = event_type
            self.content = content
            self.content_raw = content_raw
            self.target = target
            self.chan = channel
            self.nick = nick
            self.user = user
            self.host = host
            self.mask = mask
            # clients-specific parameters
            self.irc_raw = irc_raw
            self.irc_tags = irc_tags
            self.irc_prefix = irc_prefix
            self.irc_command = irc_command
            self.irc_paramlist = irc_paramlist
            self.irc_ctcp_text = irc_ctcp_text

    def __len__(self) -> int:
        return len(self.__dict__)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__dict__)

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError as e:
            raise KeyError(item) from e

    async def prepare(self):
        """
        Initializes this event to be run through it's hook

        Mainly, initializes a database object on this event, if the hook requires it.

        This method is for when the hook is *not* threaded (event.hook.threaded is False).
        If you need to add a db to a threaded hook, use prepare_threaded.
        """

        if self.hook is None:
            raise ValueError("event.hook is required to prepare an event")

        if "db" in self.hook.required_args:
            # logger.debug("Opening database session for {}:threaded=False".format(self.hook.description))

            # we're running a coroutine hook with a db, so initialise an executor pool
            self.db_executor = concurrent.futures.ThreadPoolExecutor(1)
            # be sure to initialize the db in the database executor, so it will be accessible in that thread.
            self.db = await self.async_call(Session)

    def prepare_threaded(self):
        """
        Initializes this event to be run through it's hook

        Mainly, initializes the database object on this event, if the hook requires it.

        This method is for when the hook is threaded (event.hook.threaded is True).
        If you need to add a db to a coroutine hook, use prepare.
        """

        if self.hook is None:
            raise ValueError("event.hook is required to prepare an event")

        if "db" in self.hook.required_args:
            # logger.debug("Opening database session for {}:threaded=True".format(self.hook.description))

            self.db = Session()

    async def close(self):
        """
        Closes this event after running it through it's hook.

        Mainly, closes the database connection attached to this event (if any).

        This method is for when the hook is *not* threaded (event.hook.threaded is False).
        If you need to add a db to a threaded hook, use close_threaded.
        """
        if self.hook is None:
            raise ValueError("event.hook is required to close an event")

        if self.db is not None:
            # logger.debug("Closing database session for {}:threaded=False".format(self.hook.description))
            # be sure the close the database in the database executor, as it is only accessable in that one thread
            await self.async_call(self.db.close)
            self.db = None

    def close_threaded(self):
        """
        Closes this event after running it through it's hook.

        Mainly, closes the database connection attached to this event (if any).

        This method is for when the hook is threaded (event.hook.threaded is True).
        If you need to add a db to a coroutine hook, use close.
        """
        if self.hook is None:
            raise ValueError("event.hook is required to close an event")

        if self.db is not None:
            # logger.debug("Closing database session for {}:threaded=True".format(self.hook.description))
            self.db.close()
            self.db = None

    @property
    def event(self):
        return self

    @property
    def loop(self):
        return self.bot.loop

    @property
    def logger(self):
        return logger

    def message(self, message, target=None):
        """sends a message to a specific or current channel/user"""
        if target is None:
            if self.chan is None:
                raise ValueError(
                    "Target must be specified when chan is not assigned"
                )

            target = self.chan

        self.conn.message(target, message)

    def admin_log(self, message, broadcast=False):
        """Log a message in the current connections admin log

        :param message: The message to log
        :param broadcast: Should this be broadcast to all connections
        """
        conns = [self.conn] if not broadcast else self.bot.connections.values()

        for conn in conns:
            if conn and conn.connected:
                conn.admin_log(message, console=not broadcast)

    def reply(self, *messages, target=None):
        """sends a message to the current channel/user with a prefix"""
        reply_ping = self.conn.config.get("reply_ping", True)
        if target is None:
            if self.chan is None:
                raise ValueError(
                    "Target must be specified when chan is not assigned"
                )

            target = self.chan

        if not messages:
            # if there are no messages specified, don't do anything
            return

        if target == self.nick or not reply_ping:
            self.conn.message(target, *messages)
        else:
            self.conn.message(
                target, "({}) {}".format(self.nick, messages[0]), *messages[1:]
            )

    def action(self, message, target=None):
        """sends an action to the current channel/user
        or a specific channel/user
        """
        if target is None:
            if self.chan is None:
                raise ValueError(
                    "Target must be specified when chan is not assigned"
                )

            target = self.chan

        self.conn.action(target, message)

    def ctcp(self, message, ctcp_type, target=None):
        """sends an ctcp to the current channel/user or a specific channel/user"""
        if target is None:
            if self.chan is None:
                raise ValueError(
                    "Target must be specified when chan is not assigned"
                )

            target = self.chan

        if not hasattr(self.conn, "ctcp"):
            raise ValueError("CTCP can only be used on IRC connections")

        # noinspection PyUnresolvedReferences
        self.conn.ctcp(target, ctcp_type, message)

    def notice(self, message, target=None):
        """sends a notice to the current channel/user or a specific channel/user"""
        avoid_notices = self.conn.config.get("avoid_notices", False)
        if target is None:
            if self.nick is None:
                raise ValueError(
                    "Target must be specified when nick is not assigned"
                )

            target = self.nick

        # we have a config option to avoid noticing user and PM them instead, so we use it here
        if avoid_notices:
            self.conn.message(target, message)
        else:
            self.conn.notice(target, message)

    def has_permission(self, permission, notice=True):
        """returns whether or not the current user has a given permission"""
        if not self.mask:
            raise ValueError("has_permission requires mask is not assigned")

        return self.conn.permissions.has_perm_mask(
            self.mask, permission, notice=notice
        )

    async def check_permission(self, permission, notice=True):
        """returns whether or not the current user has a given permission"""
        if self.has_permission(permission, notice=notice):
            return True

        for perm_hook in self.bot.plugin_manager.perm_hooks[permission]:
            ok, res = await self.bot.plugin_manager.internal_launch(
                perm_hook, Event(base_event=self, hook=perm_hook)
            )
            if ok and res:
                return True

        return False

    async def check_permissions(self, *perms, notice=True):
        for perm in perms:
            if await self.check_permission(perm, notice=notice):
                return True

        return False

    async def async_call(self, func, *args, **kwargs):
        if self.db_executor is not None:
            executor = self.db_executor
        else:
            executor = None

        part = partial(func, *args, **kwargs)
        result = await self.loop.run_in_executor(executor, part)
        return result

    def is_nick_valid(self, nick):
        """
        Returns whether a nick is valid for a given connection
        :param nick: The nick to check
        :return: Whether or not it is valid
        """
        return self.conn.is_nick_valid(nick)


class CommandEvent(Event):
    def __init__(
        self,
        *,
        bot=None,
        hook,
        text,
        triggered_command,
        cmd_prefix,
        conn=None,
        base_event=None,
        event_type=None,
        content=None,
        content_raw=None,
        target=None,
        channel=None,
        nick=None,
        user=None,
        host=None,
        mask=None,
        irc_raw=None,
        irc_prefix=None,
        irc_command=None,
        irc_paramlist=None,
    ):
        """
        :param text: The arguments for the command
        :param triggered_command: The command that was triggered
        """
        super().__init__(
            bot=bot,
            hook=hook,
            conn=conn,
            base_event=base_event,
            event_type=event_type,
            content=content,
            content_raw=content_raw,
            target=target,
            channel=channel,
            nick=nick,
            user=user,
            host=host,
            mask=mask,
            irc_raw=irc_raw,
            irc_prefix=irc_prefix,
            irc_command=irc_command,
            irc_paramlist=irc_paramlist,
        )
        self.hook = hook
        self.text = text
        self.doc = self.hook.doc
        self.triggered_command = triggered_command
        self.triggered_prefix = cmd_prefix

    def notice_doc(self, target=None):
        """sends a notice containing this command's docstring to
        the current channel/user or a specific channel/user
        """
        if self.triggered_command is None:
            raise ValueError("Triggered command not set on this event")

        if self.hook.doc is None:
            message = "{}{} requires additional arguments.".format(
                self.triggered_prefix, self.triggered_command
            )
        else:
            message = "{}{} {}".format(
                self.triggered_prefix, self.triggered_command, self.hook.doc
            )

        self.notice(message, target=target)


class RegexEvent(Event):
    def __init__(
        self,
        *,
        bot=None,
        hook,
        match,
        conn=None,
        base_event=None,
        event_type=None,
        content=None,
        content_raw=None,
        target=None,
        channel=None,
        nick=None,
        user=None,
        host=None,
        mask=None,
        irc_raw=None,
        irc_prefix=None,
        irc_command=None,
        irc_paramlist=None,
    ):
        """
        :param: match: The match objected returned by the regex search method
        """
        super().__init__(
            bot=bot,
            conn=conn,
            hook=hook,
            base_event=base_event,
            event_type=event_type,
            content=content,
            content_raw=content_raw,
            target=target,
            channel=channel,
            nick=nick,
            user=user,
            host=host,
            mask=mask,
            irc_raw=irc_raw,
            irc_prefix=irc_prefix,
            irc_command=irc_command,
            irc_paramlist=irc_paramlist,
        )
        self.match = match


class CapEvent(Event):
    def __init__(self, *args, cap, cap_param=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cap = cap
        self.cap_param = cap_param


class IrcOutEvent(Event):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsed_line = None

    async def prepare(self):
        await super().prepare()

        if "parsed_line" in self.hook.required_args:
            try:
                self.parsed_line = Message.parse(self.line)
            except Exception:
                logger.exception(
                    "Unable to parse line requested by hook %s", self.hook
                )
                self.parsed_line = None

    def prepare_threaded(self):
        super().prepare_threaded()

        if "parsed_line" in self.hook.required_args:
            try:
                self.parsed_line = Message.parse(self.line)
            except Exception:
                logger.exception(
                    "Unable to parse line requested by hook %s", self.hook
                )
                self.parsed_line = None

    @property
    def line(self):
        return str(self.irc_raw)


class PostHookEvent(Event):
    def __init__(
        self,
        *args,
        launched_hook=None,
        launched_event=None,
        result=None,
        error=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.launched_hook = launched_hook
        self.launched_event = launched_event
        self.result = result
        self.error = error
