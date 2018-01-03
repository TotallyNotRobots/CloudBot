import asyncio
import collections
import gc
import logging
import os
import re
import time
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.schema import MetaData
from watchdog.observers import Observer

from cloudbot.client import Client
from cloudbot.clients.irc import IrcClient, irc_clean
from cloudbot.config import Config
from cloudbot.event import Event, CommandEvent, RegexEvent, EventType
from cloudbot.hook import Action
from cloudbot.plugin import PluginManager
from cloudbot.reloader import PluginReloader, ConfigReloader
from cloudbot.util import database, formatting, async_util

try:
    from cloudbot.web.main import WebInterface

    web_installed = True
except ImportError:
    WebInterface = None
    web_installed = False

logger = logging.getLogger("cloudbot")


def clean_name(n):
    """strip all spaces and capitalization
    :type n: str
    :rtype: str
    """
    return re.sub('[^A-Za-z0-9_]+', '', n.replace(" ", "_"))


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
        self.data_dir = os.path.abspath('data')
        if not os.path.exists(self.data_dir):
            logger.debug("Data folder not found, creating.")
            os.mkdir(self.data_dir)

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

        # create web interface
        if self.config.get("web", {}).get("enabled", False) and web_installed:
            self.web = WebInterface(self)

        # set botvars so plugins can access when loading
        database.metadata = self.db_metadata
        database.base = self.db_base

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
            server = config['connection']['server']
            port = config['connection'].get('port', 6667)
            local_bind = (config['connection'].get('bind_addr', False), config['connection'].get('bind_port', 0))
            if local_bind[0] is False:
                local_bind = False

            self.connections[name] = IrcClient(self, name, nick, config=config, channels=config['channels'],
                                               server=server, port=port, use_ssl=config['connection'].get('ssl', False),
                                               local_bind=local_bind)
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
            if not connection.connected:
                # Don't close a connection that hasn't connected
                continue
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
        yield from self.plugin_manager.load_all(os.path.abspath("plugins"))

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

        # Connect to servers
        yield from asyncio.gather(*[conn.try_connect() for conn in self.connections.values()], loop=self.loop)

        # Activate web interface.
        if self.config.get("web", {}).get("enabled", False) and web_installed:
            self.web.start()

        # Run a manual garbage collection cycle, to clean up any unused objects created during initialization
        gc.collect()

    @asyncio.coroutine
    def process(self, event):
        """
        :type event: Event
        """
        run_before_tasks = []
        tasks = []
        command_prefix = event.conn.config.get('command_prefix', '.')
        halted = False

        def add_hook(hook, _event, _run_before=False):
            nonlocal halted
            if halted:
                return False

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

        if event.type is EventType.message:
            # Commands
            if event.chan.lower() == event.nick.lower():  # private message, no command prefix
                command_re = r'(?i)^(?:[{}]?|{}[,;:]+\s+)(\w+)(?:$|\s+)(.*)'
            else:
                command_re = r'(?i)^(?:[{}]|{}[,;:]+\s+)(\w+)(?:$|\s+)(.*)'

            cmd_match = re.match(
                command_re.format(command_prefix, event.conn.nick),
                event.content_raw
            )

            if cmd_match:
                command = cmd_match.group(1).lower()
                text = irc_clean(cmd_match.group(2).strip())
                if command in self.plugin_manager.commands:
                    command_hook = self.plugin_manager.commands[command]
                    command_event = CommandEvent(hook=command_hook, text=text,
                                                 triggered_command=command, base_event=event)
                    add_hook(command_hook, command_event)
                else:
                    potential_matches = []
                    for potential_match, plugin in self.plugin_manager.commands.items():
                        if potential_match.startswith(command):
                            potential_matches.append((potential_match, plugin))
                    if potential_matches:
                        if len(potential_matches) == 1:
                            command_hook = potential_matches[0][1]
                            command_event = CommandEvent(hook=command_hook, text=text,
                                                         triggered_command=command, base_event=event)
                            add_hook(command_hook, command_event)
                        else:
                            event.notice("Possible matches: {}".format(
                                formatting.get_text_list([command for command, plugin in potential_matches])))

            # Regex hooks
            regex_matched = False
            for regex, regex_hook in self.plugin_manager.regex_hooks:
                if not regex_hook.run_on_cmd and cmd_match:
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
