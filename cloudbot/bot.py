import asyncio
import collections
import gc
import importlib
import logging
import re
import time
from functools import partial
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.schema import MetaData
from watchdog.observers import Observer

from cloudbot.client import Client, CLIENTS
from cloudbot.config import Config
from cloudbot.event import Event, CommandEvent, RegexEvent, EventType
from cloudbot.hook import Action
from cloudbot.plugin import PluginManager
from cloudbot.reloader import PluginReloader, ConfigReloader
from cloudbot.util import database, formatting, async_util

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
    :type db_factory: sqlalchemy.orm.session.sessionmaker
    :type db_session: sqlalchemy.orm.scoping.scoped_session
    :type db_metadata: sqlalchemy.sql.schema.MetaData
    """

    def __init__(self, loop=asyncio.get_event_loop()):
        # basic variables
        self.base_dir = Path().resolve()
        self.loop = loop
        self.start_time = time.time()
        self.running = True
        # future which will be called when the bot stopsIf you
        self.stopped_future = async_util.create_future(self.loop)

        # stores each bot server connection
        self.connections = {}

        # for plugins
        self.logger = logger

        # for plugins to abuse
        self.memory = collections.defaultdict()

        # declare and create data folder
        self.data_dir = self.base_dir / "data"
        if not self.data_dir.exists():
            logger.debug("Data folder not found, creating...")
            self.data_dir.mkdir(parents=True)
            logger.debug("Done.")

        self.default_plugin_directory = self.base_dir / "plugins"

        # set up config
        self.config = Config(self)
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
        self.db_factory = sessionmaker(bind=self.db_engine)
        self.db_session = scoped_session(self.db_factory)
        self.db_metadata = MetaData()
        self.db_base = declarative_base(metadata=self.db_metadata, bind=self.db_engine)

        # set botvars so plugins can access when loading
        database.metadata = self.db_metadata
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
        restart = self.loop.run_until_complete(self.stopped_future)
        self.loop.run_until_complete(self.plugin_manager.unload_all())
        self.loop.close()
        return restart

    def create_connections(self):
        """ Create a BotConnection for all the networks defined in the config """
        for config in self.config['connections']:
            # strip all spaces and capitalization from the connection name
            name = clean_name(config['name'])
            nick = config['nick']
            _type = config.get("type", "irc")

            self.connections[name] = CLIENTS[_type](self, name, nick, config=config, channels=config['channels'])
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
        # Give the stopped_future a result, so that run() will exit
        self.stopped_future.set_result(restart)

    @asyncio.coroutine
    def restart(self, reason=None):
        """shuts the bot down and restarts it"""
        yield from self.stop(reason=reason, restart=True)

    @asyncio.coroutine
    def _init_routine(self):
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

    def load_clients(self):
        """
        Load all clients from the "clients" directory
        """
        client_dir = self.base_dir / "cloudbot" / "clients"
        for path in client_dir.rglob('*.py'):
            rel_path = path.relative_to(self.base_dir)
            mod_path = '.'.join(rel_path.parts).rsplit('.', 1)[0]
            importlib.import_module(mod_path)

    @asyncio.coroutine
    def process(self, event):
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
            elif hook.action is Action.HALTTYPE:
                return False
            return True

        # Raw IRC hook
        for raw_hook in self.plugin_manager.catch_all_triggers:
            # run catch-all coroutine hooks before all others - TODO: Make this a plugin argument
            run_before = not raw_hook.threaded
            if not add_hook(raw_hook, Event(hook=raw_hook, base_event=event), _run_before=run_before):
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
                            commands = sorted(command for command, plugin in potential_matches)
                            txt_list = formatting.get_text_list(commands)
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

        # Run the tasks
        yield from asyncio.gather(*run_before_tasks, loop=self.loop)
        yield from asyncio.gather(*tasks, loop=self.loop)
