import asyncio
import collections
import gc
import logging
import os
import re
import time
from functools import partial
from pathlib import Path
from typing import Type

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from venusian import Scanner
from watchdog.observers import Observer

from cloudbot import clients
from cloudbot.client import Client
from cloudbot.config import Config
from cloudbot.event import CommandEvent, Event, EventType, RegexEvent
from cloudbot.hook import Action
from cloudbot.plugin import PluginManager
from cloudbot.reloader import ConfigReloader, PluginReloader
from cloudbot.util import async_util, database, formatting
from cloudbot.util.mapping import KeyFoldDict

logger = logging.getLogger("cloudbot")


class BotInstanceHolder:
    def __init__(self):
        self._instance = None

    def get(self):
        # type: () -> CloudBot
        return self._instance

    def set(self, value):
        # type: (CloudBot) -> None
        self._instance = value

    @property
    def config(self):
        # type: () -> Config
        if not self.get():
            raise ValueError("No bot instance available")

        return self.get().config


# Store a global instance of the bot to allow easier access to global data
bot = BotInstanceHolder()


def clean_name(n):
    """strip all spaces and capitalization
    :type n: str
    :rtype: str
    """
    return re.sub("[^A-Za-z0-9_]+", "", n.replace(" ", "_"))


def get_cmd_regex(event):
    conn = event.conn
    is_pm = event.chan.lower() == event.nick.lower()
    command_prefix = re.escape(conn.config.get("command_prefix", "."))
    conn_nick = re.escape(event.conn.nick)
    cmd_re = re.compile(
        r"""
        ^
        # Prefix or nick
        (?:
            (?P<prefix>["""
        + command_prefix
        + r"""])"""
        + ("?" if is_pm else "")
        + r"""
            |
            """
        + conn_nick
        + r"""[,;:]+\s+
        )
        (?P<command>\w+)  # Command
        (?:$|\s+)
        (?P<text>.*)     # Text
        """,
        re.IGNORECASE | re.VERBOSE,
    )
    return cmd_re


class CloudBot:
    """
    :type start_time: float
    :type running: bool
    :type connections: dict[str, Client]
    :type data_dir: bytes
    :type config: core.config.Config
    :type plugin_manager: PluginManager
    :type plugin_reloader: PluginReloader
    :type db_engine: sqlalchemy.engine.Engine
    :type db_factory: sqlalchemy.orm.session.sessionmaker
    :type db_session: sqlalchemy.orm.scoping.scoped_session
    :type db_metadata: sqlalchemy.sql.schema.MetaData
    :type loop: asyncio.events.AbstractEventLoop
    :type stopped_future: asyncio.Future
    :param: stopped_future: Future that will be given a result when the bot has stopped.
    """

    def __init__(self, loop=asyncio.get_event_loop()):
        if bot.get():
            raise ValueError("There seems to already be a bot running!")

        bot.set(self)
        # basic variables
        self.base_dir = Path().resolve()
        self.loop = loop
        self.start_time = time.time()
        self.running = True
        self.clients = {}
        # future which will be called when the bot stopsIf you
        self.stopped_future = async_util.create_future(self.loop)

        # stores each bot server connection
        self.connections = KeyFoldDict()

        # for plugins
        self.logger = logger

        # for plugins to abuse
        self.memory = collections.defaultdict()

        # declare and create data folder
        self.data_dir = os.path.abspath("data")
        if not os.path.exists(self.data_dir):
            logger.debug("Data folder not found, creating.")
            os.mkdir(self.data_dir)

        # set up config
        self.config = Config(self)
        logger.debug("Config system initialised.")

        # set values for reloading
        reloading_conf = self.config.get("reloading", {})
        self.plugin_reloading_enabled = reloading_conf.get(
            "plugin_reloading", False
        )
        self.config_reloading_enabled = reloading_conf.get(
            "config_reloading", True
        )

        # this doesn't REALLY need to be here but it's nice
        self.repo_link = self.config.get(
            "repo_link", "https://github.com/TotallyNotRobots/CloudBot/"
        )
        self.user_agent = self.config.get(
            "user_agent", "CloudBot/3.0 - CloudBot Refresh <{repo_link}>"
        ).format(repo_link=self.repo_link)

        # setup db
        db_path = self.config.get("database", "sqlite:///cloudbot.db")
        self.db_engine = create_engine(db_path)
        self.db_factory = sessionmaker(bind=self.db_engine)
        self.db_session = scoped_session(self.db_factory)
        self.db_metadata = database.metadata
        self.db_base = declarative_base(
            metadata=self.db_metadata, bind=self.db_engine
        )

        # set botvars so plugins can access when loading
        database.base = self.db_base

        logger.debug("Database system initialised.")

        # Bot initialisation complete
        logger.debug("Bot setup completed.")

        self.load_clients()

        # create bot connections
        self.create_connections()

        self.observer = Observer()

        if self.plugin_reloading_enabled:
            self.plugin_reloader = PluginReloader(self)

        if self.config_reloading_enabled:
            self.config_reloader = ConfigReloader(self)

        self.plugin_manager = PluginManager(self)

    def run(self):
        """
        Starts CloudBot.
        This will load plugins, connect to IRC, and process input.
        :return: True if CloudBot should be restarted, False otherwise
        :rtype: bool
        """
        # Initializes the bot, plugins and connections
        self.loop.run_until_complete(self._init_routine())
        # Wait till the bot stops. The stopped_future will be set to True to restart, False otherwise
        logger.debug("Init done")
        restart = self.loop.run_until_complete(self.stopped_future)
        logger.debug("Waiting for plugin unload")
        self.loop.run_until_complete(self.plugin_manager.unload_all())
        logger.debug("Unload complete")
        self.loop.close()
        return restart

    def get_client(self, name: str) -> Type[Client]:
        return self.clients[name]

    def register_client(self, name, cls):
        self.clients[name] = cls

    def create_connections(self):
        """ Create a BotConnection for all the networks defined in the config """
        for config in self.config["connections"]:
            # strip all spaces and capitalization from the connection name
            name = clean_name(config["name"])
            nick = config["nick"]
            _type = config.get("type", "irc")

            self.connections[name] = self.get_client(_type)(
                self,
                _type,
                name,
                nick,
                config=config,
                channels=config["channels"],
            )
            logger.debug("[%s] Created connection.", name)

    async def stop(self, reason=None, *, restart=False):
        """quits all networks and shuts the bot down"""
        logger.info("Stopping bot.")

        if self.config_reloading_enabled:
            logger.debug("Stopping config reloader.")
            self.config_reloader.stop()

        if self.plugin_reloading_enabled:
            logger.debug("Stopping plugin reloader.")
            self.plugin_reloader.stop()

        self.observer.stop()

        logger.debug("Stopping connect loops and shutting down clients")
        for connection in self.connections.values():
            connection.active = False
            if not connection.cancelled_future.done():
                connection.cancelled_future.set_result(None)

            if not connection.connected:
                # Don't quit a connection that hasn't connected
                continue
            logger.debug("[%s] Closing connection.", connection.name)

            connection.quit(reason)

        logger.debug("Done.")

        logger.debug("Sleeping to let clients quit")
        await asyncio.sleep(1.0)  # wait for 'QUIT' calls to take affect
        logger.debug("Sleep done.")

        logger.debug("Closing clients")
        for connection in self.connections.values():
            connection.close()

        logger.debug("All clients closed")

        self.running = False
        # Give the stopped_future a result, so that run() will exit
        logger.debug("Setting future result for shutdown")
        self.stopped_future.set_result(restart)

    async def restart(self, reason=None):
        """shuts the bot down and restarts it"""
        await self.stop(reason=reason, restart=True)

    async def _init_routine(self):
        # Load plugins
        await self.plugin_manager.load_all(os.path.abspath("plugins"))

        # If we we're stopped while loading plugins, cancel that and just stop
        if not self.running:
            logger.info("Killed while loading, exiting")
            return

        if self.plugin_reloading_enabled:
            # start plugin reloader
            self.plugin_reloader.start(os.path.abspath("plugins"))

        if self.config_reloading_enabled:
            self.config_reloader.start()

        self.observer.start()

        for conn in self.connections.values():
            conn.active = True

        # Connect to servers
        await asyncio.gather(
            *[conn.try_connect() for conn in self.connections.values()],
            loop=self.loop,
        )
        logger.debug("Connections created.")

        # Run a manual garbage collection cycle, to clean up any unused objects created during initialization
        gc.collect()

    def load_clients(self):
        """
        Load all clients from the "clients" directory
        """
        scanner = Scanner(bot=self)
        scanner.scan(clients, categories=["cloudbot.client"])

    async def process(self, event):
        """
        :type event: Event
        """
        run_before_tasks = []
        tasks = []
        halted = False

        def add_hook(hook, _event, _run_before=False):
            nonlocal halted
            if halted:
                return False

            if hook.clients and _event.conn.type not in hook.clients:
                return True

            coro = self.plugin_manager.launch(hook, _event)
            if _run_before:
                run_before_tasks.append(coro)
            else:
                tasks.append(coro)

            if hook.action is Action.HALTALL:
                halted = True
                return False

            if hook.action is Action.HALTTYPE:
                return False

            return True

        # Raw IRC hook
        for raw_hook in self.plugin_manager.catch_all_triggers:
            # run catch-all coroutine hooks before all others - TODO: Make this a plugin argument
            run_before = not raw_hook.threaded
            if not add_hook(
                raw_hook,
                Event(hook=raw_hook, base_event=event),
                _run_before=run_before,
            ):
                # The hook has an action of Action.HALT* so stop adding new tasks
                break

        if event.irc_command in self.plugin_manager.raw_triggers:
            for raw_hook in self.plugin_manager.raw_triggers[event.irc_command]:
                if not add_hook(
                    raw_hook, Event(hook=raw_hook, base_event=event)
                ):
                    # The hook has an action of Action.HALT* so stop adding new tasks
                    break

        # Event hooks
        if event.type in self.plugin_manager.event_type_hooks:
            for event_hook in self.plugin_manager.event_type_hooks[event.type]:
                if not add_hook(
                    event_hook, Event(hook=event_hook, base_event=event)
                ):
                    # The hook has an action of Action.HALT* so stop adding new tasks
                    break

        matched_command = False

        if event.type is EventType.message:
            # Commands
            cmd_match = get_cmd_regex(event).match(event.content)

            if cmd_match:
                command_prefix = event.conn.config.get("command_prefix", ".")
                prefix = cmd_match.group("prefix") or command_prefix[0]
                command = cmd_match.group("command").lower()
                text = cmd_match.group("text").strip()
                cmd_event = partial(
                    CommandEvent,
                    text=text,
                    triggered_command=command,
                    base_event=event,
                    cmd_prefix=prefix,
                )
                if command in self.plugin_manager.commands:
                    command_hook = self.plugin_manager.commands[command]
                    command_event = cmd_event(hook=command_hook)
                    add_hook(command_hook, command_event)
                    matched_command = True
                else:
                    potential_matches = []
                    for (
                        potential_match,
                        plugin,
                    ) in self.plugin_manager.commands.items():
                        if potential_match.startswith(command):
                            potential_matches.append((potential_match, plugin))

                    if potential_matches:
                        matched_command = True
                        if len(potential_matches) == 1:
                            command_hook = potential_matches[0][1]
                            command_event = cmd_event(hook=command_hook)
                            add_hook(command_hook, command_event)
                        else:
                            commands = sorted(
                                command for command, plugin in potential_matches
                            )
                            txt_list = formatting.get_text_list(commands)
                            event.notice(
                                "Possible matches: {}".format(txt_list)
                            )

        if event.type in (EventType.message, EventType.action):
            # Regex hooks
            regex_matched = False
            for regex, regex_hook in self.plugin_manager.regex_hooks:
                if not regex_hook.run_on_cmd and matched_command:
                    continue

                if regex_hook.only_no_match and regex_matched:
                    continue

                regex_match = regex.search(event.content)
                if regex_match:
                    regex_matched = True
                    regex_event = RegexEvent(
                        hook=regex_hook, match=regex_match, base_event=event
                    )
                    if not add_hook(regex_hook, regex_event):
                        # The hook has an action of Action.HALT* so stop adding new tasks
                        break

        # Run the tasks
        await asyncio.gather(*run_before_tasks, loop=self.loop)
        await asyncio.gather(*tasks, loop=self.loop)

    async def reload_config(self):
        self.config.load_config()

        # reload permissions
        for connection in self.connections.values():
            connection.reload()

        event = Event(bot=self)

        tasks = [
            self.plugin_manager.launch(hook, event)
            for hook in self.plugin_manager.config_hooks
        ]

        await asyncio.gather(*tasks)
