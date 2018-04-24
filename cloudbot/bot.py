import asyncio
import gc
import importlib
import logging
import re
import time
from collections import defaultdict
from functools import partial
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from watchdog.observers import Observer

from .client import Client
from .config import Config
from .event import Event, CommandEvent, RegexEvent, EventType
from .hooks.actions import Action
from .plugin import PluginManager
from .reloader import PluginReloader, ConfigReloader
from .util.async_util import run_coroutine_threadsafe, create_future
from .util.database import ContextSession
from .util.formatting import get_text_list

logger = logging.getLogger("cloudbot")


def clean_name(n):
    """strip all spaces and capitalization
    :type n: str
    :rtype: str
    """
    return re.sub('[^A-Za-z0-9_]+', '', n.replace(" ", "_"))


def get_cmd_regex(event):
    conn = event.conn
    is_pm = event.chan.lower() == event.nick.lower()
    command_prefix = re.escape(conn.config.get('command_prefix', '.'))
    conn_nick = re.escape(event.conn.nick)
    cmd_re = re.compile(
        r"""
        ^
        # Prefix or nick
        (?:
            (?P<prefix>[""" + command_prefix + r"""])""" + ('?' if is_pm else '') + r"""
            |
            """ + conn_nick + r"""[,;:]+\s+
        )
        (?P<command>\w+)  # Command
        (?:$|\s+)
        (?P<text>.*)     # Text
        """,
        re.IGNORECASE | re.VERBOSE
    )
    return cmd_re


class CloudBot:
    """
    :type base_dir: Path
    :type loop: asyncio.events.AbstractEventLoop
    :type start_time: float
    :type running: bool
    :type stopped_future: asyncio.Future
    :param: stopped_future: Future that will be given a result when the bot has stopped.
    :type connections: dict[str, Client]
    :type logger: logging.Logger
    :type memory: dict
    :type data_dir: Path
    :type config: core.config.Config
    :type user_agent: str
    :type plugin_manager: PluginManager
    :type config_reloader: ConfigReloader
    :type plugin_reloader: PluginReloader
    :type db_engine: sqlalchemy.engine.Engine
    :type db_session: sqlalchemy.orm.scoping.scoped_session
    """

    def __init__(self, loop=asyncio.get_event_loop()):
        # basic variables
        self.base_dir = Path().resolve()
        self.loop = loop
        self.start_time = time.time()
        self.running = True
        # future which will be called when the bot stopsIf you
        self.stopped_future = create_future(self.loop)

        # stores each bot server connection
        self.connections = {}

        self.event_queue = asyncio.Queue()

        # for plugins
        self.logger = logger

        # for plugins to abuse
        self.memory = defaultdict()

        # declare and create data folder
        self.data_dir = self.base_dir / "data"
        if not self.data_dir.exists():
            logger.debug("Data folder not found, creating...")
            self.data_dir.mkdir(parents=True)
            logger.debug("Done.")

        self.default_plugin_directory = self.base_dir / "plugins"

        # set up config
        self.config = Config()
        logger.debug("Config system initialised.")

        # set values for reloading
        reloading_conf = self.config.get("reloading", {})
        self.plugin_reloading_enabled = reloading_conf.get("plugin_reloading", False)
        self.config_reloading_enabled = reloading_conf.get("config_reloading", True)

        # this doesn't REALLY need to be here but it's nice
        self.user_agent = self.config.get('user_agent', 'CloudBot/3.0 - CloudBot Refresh '
                                                        '<https://github.com/CloudBotIRC/CloudBot/>')

        # setup db
        db_path = self.config.get('database', 'sqlite:///cloudbot.db')
        self.db_engine = create_engine(db_path)
        self.db_session = scoped_session(sessionmaker(bind=self.db_engine))

        logger.debug("Database system initialised.")

        # Bot initialisation complete
        logger.debug("Bot setup completed.")

        # create bot connections
        self.create_connections()

        self.observer = Observer()

        if self.plugin_reloading_enabled:
            self.plugin_reloader = PluginReloader(self)

        if self.config_reloading_enabled:
            self.config_reloader = ConfigReloader(self)

        self.plugin_manager = PluginManager(self)

        self.reload_config()

    def get_db_session(self):
        return ContextSession(self.db_session())

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
        self.loop.run_until_complete(self.main_loop())
        restart = self.loop.run_until_complete(self.stopped_future)
        self.loop.run_until_complete(self.plugin_manager.unload_all())
        self.loop.run_until_complete(self.plugin_manager.shutdown())
        self.loop.close()
        return restart

    def reload_config(self):
        """
        Called when the config is reloaded
        """
        self.config.load_config()
        for connection in self.config['connections']:
            name = clean_name(connection['name'])
            try:
                conn = self.connections[name]
            except LookupError:
                self.connections[name] = conn = self._make_connection(name, connection)
                logger.debug("[{}] Reloading config created connection.".format(conn.name))
                run_coroutine_threadsafe(conn.connect(), self.loop)

            conn.reload_config()

    def _make_connection(self, name, config):
        """
        :type name: str
        :type config: dict
        :rtype: Client
        """
        _type = config.get("type", "irc")

        client = self.get_client(_type)

        client_cls = getattr(client, 'get_client')()

        return client_cls(self, name, config)

    def create_connections(self):
        """ Create a Client for all the networks defined in the config """
        for config in self.config['connections']:
            # strip all spaces and capitalization from the connection name
            name = clean_name(config['name'])
            self.connections[name] = self._make_connection(name, config)
            logger.debug("[{}] Created connection.".format(name))

    @asyncio.coroutine
    def stop(self, reason=None, *, restart=False):
        """quits all networks and shuts the bot down"""
        logger.info("Stopping bot.")

        if self.config_reloading_enabled:
            logger.debug("Stopping config reloader.")
            self.config_reloader.stop()

        if self.plugin_reloading_enabled:
            logger.debug("Stopping plugin reloader.")
            self.plugin_reloader.stop()

        self.observer.stop()

        for connection in self.connections.values():
            if not connection.connected:
                # Don't quit a connection that hasn't connected
                continue
            logger.debug("[{}] Closing connection.".format(connection.name))

            connection.quit(reason)

        yield from asyncio.sleep(1.0)  # wait for 'QUIT' calls to take affect

        for connection in self.connections.values():
            connection.close()

        self.running = False
        self.event_queue.put_nowait(None)
        # Give the stopped_future a result, so that run() will exit
        self.stopped_future.set_result(restart)

    @asyncio.coroutine
    def restart(self, reason=None):
        """shuts the bot down and restarts it"""
        yield from self.stop(reason=reason, restart=True)

    @asyncio.coroutine
    def _init_routine(self):
        yield from self.plugin_manager.start()
        # Load plugins
        yield from self.plugin_manager.load_all(self.default_plugin_directory)

        # If we we're stopped while loading plugins, cancel that and just stop
        if not self.running:
            logger.info("Killed while loading, exiting")
            return

        if self.plugin_reloading_enabled:
            # start plugin reloader
            self.plugin_reloader.start(str(self.default_plugin_directory))

        if self.config_reloading_enabled:
            self.config_reloader.start()

        self.observer.start()

        # Connect to servers
        yield from asyncio.gather(*[conn.connect() for conn in self.connections.values()], loop=self.loop)

        # Run a manual garbage collection cycle, to clean up any unused objects created during initialization
        gc.collect()

    def get_client(self, name):
        """
        :type name: str
        :rtype: Client
        """
        client = importlib.import_module(".clients." + name, package=__package__)
        return client

    def _get_tasks(self, event):
        """
        :type event: Event
        """
        tasks = []
        halted = False

        def add_hook(hook, _event, _run_before=False):
            nonlocal halted
            if halted:
                return False

            if hook.clients and _event.conn.type not in hook.clients:
                return True

            # coro = self.plugin_manager.launch(hook, _event)
            tasks.append((hook, _event))

            if hook.action is Action.HALTALL:
                halted = True
                return False
            elif hook.action is Action.HALTTYPE:
                return False
            return True

        # Raw IRC hook
        for raw_hook in self.plugin_manager.catch_all_triggers:
            if not add_hook(raw_hook, Event(hook=raw_hook, base_event=event)):
                # The hook has an action of Action.HALT* so stop adding new tasks
                break

        if event.irc_command in self.plugin_manager.raw_triggers:
            for raw_hook in self.plugin_manager.raw_triggers[event.irc_command]:
                if not add_hook(raw_hook, Event(hook=raw_hook, base_event=event)):
                    # The hook has an action of Action.HALT* so stop adding new tasks
                    break

        # Event hooks
        if event.type in self.plugin_manager.event_type_hooks:
            for event_hook in self.plugin_manager.event_type_hooks[event.type]:
                if not add_hook(event_hook, Event(hook=event_hook, base_event=event)):
                    # The hook has an action of Action.HALT* so stop adding new tasks
                    break

        matched_command = False

        if event.type is EventType.message:
            # Commands
            cmd_match = get_cmd_regex(event).match(event.content)

            if cmd_match:
                command_prefix = event.conn.config.get('command_prefix', '.')
                prefix = cmd_match.group('prefix') or command_prefix
                command = cmd_match.group('command').lower()
                text = cmd_match.group('text').strip()
                cmd_event = partial(
                    CommandEvent, text=text, triggered_command=command, base_event=event, cmd_prefix=prefix
                )
                if command in self.plugin_manager.commands:
                    command_hook = self.plugin_manager.commands[command]
                    command_event = cmd_event(hook=command_hook)
                    add_hook(command_hook, command_event)
                    matched_command = True
                else:
                    potential_matches = []
                    for potential_match, plugin in self.plugin_manager.commands.items():
                        if potential_match.startswith(command):
                            potential_matches.append((potential_match, plugin))

                    if potential_matches:
                        matched_command = True
                        if len(potential_matches) == 1:
                            command_hook = potential_matches[0][1]
                            command_event = cmd_event(hook=command_hook)
                            add_hook(command_hook, command_event)
                        else:
                            commands = sorted(command for command, _ in potential_matches)
                            txt_list = get_text_list(commands)
                            event.notice("Possible matches: {}".format(txt_list))

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
                    regex_event = RegexEvent(hook=regex_hook, match=regex_match, base_event=event)
                    if not add_hook(regex_hook, regex_event):
                        # The hook has an action of Action.HALT* so stop adding new tasks
                        break

        tasks.sort(key=lambda t: t[0].priority)
        return tasks

    @asyncio.coroutine
    def main_loop(self):
        while self.running:
            event = yield from self.event_queue.get()
            if event is not None:
                tasks = self._get_tasks(event)
                for task in tasks:
                    self.plugin_manager.hook_queue.put_nowait(task)

            self.event_queue.task_done()
