"""
Validates all hook registrations in all plugins
"""
import asyncio
import importlib
import inspect
import re
import warnings
from numbers import Number
from pathlib import Path
from unittest import mock

from sqlalchemy import MetaData

from cloudbot.event import Event, CommandEvent, RegexEvent, CapEvent, PostHookEvent, IrcOutEvent
from cloudbot.hooks.actions import Action
from cloudbot.hooks.full import Hook
from cloudbot.plugin import Plugin
from cloudbot.util import database
from cloudbot.util.func_utils import populate_args

warnings.filterwarnings("error", module="^(cloudbot|plugins)(\..*|$)")
_Hook_init = Hook.__init__

DOC_RE = re.compile(r"^(?:(?:<.+?>|{.+?}|\[.+?\]).+?)*?-\s.+$")
PLUGINS = []


class MockBot:
    def __init__(self):
        self.loop = None


def patch_hook_init(self, _type, plugin, func_hook):
    _Hook_init(self, _type, plugin, func_hook)
    self.func_hook = func_hook


def gather_plugins():
    plugin_dir = Path("plugins")
    path_list = plugin_dir.rglob("[!_]*.py")
    return path_list


def load_plugin(plugin_path):
    path = Path(plugin_path)
    file_path = path.resolve()
    file_name = file_path.name
    # Resolve the path relative to the current directory
    plugin_path = file_path.relative_to(Path().resolve())
    title = '.'.join(plugin_path.parts[1:]).rsplit('.', 1)[0]

    module_name = "plugins.{}".format(title)

    plugin_module = importlib.import_module(module_name)

    return Plugin(str(file_path), file_name, title, plugin_module)


def get_plugins():
    if not PLUGINS:
        with mock.patch.object(database, 'metadata', new=MetaData()), \
             mock.patch.object(Hook, '__init__', new=patch_hook_init):
            PLUGINS.extend(map(load_plugin, gather_plugins()))

    return PLUGINS


def pytest_generate_tests(metafunc):
    if 'plugin' in metafunc.fixturenames:
        plugins = get_plugins()
        metafunc.parametrize('plugin', plugins, ids=[plugin.title for plugin in plugins])
    elif 'hook' in metafunc.fixturenames:
        plugins = get_plugins()
        hooks = [hook for plugin in plugins for hook_list in plugin.hooks.values() for hook in hook_list]
        metafunc.parametrize(
            'hook', hooks, ids=["{}.{}".format(hook.plugin.title, hook.function_name) for hook in hooks]
        )


HOOK_ATTR_TYPES = {
    'permissions': (list, set, frozenset, tuple),
    'single_thread': bool,
    'action': Action,
    'priority': int,

    'auto_help': bool,

    'run_on_cmd': bool,
    'only_no_match': bool,

    'interval': Number,
    'initial_interval': Number,
}


def test_hook_kwargs(hook):
    assert not hook.func_hook.kwargs, \
        "Unknown arguments '{}' passed during registration of hook '{}'".format(
            hook.func_hook.kwargs, hook.function_name
        )

    for name, types in HOOK_ATTR_TYPES.items():
        try:
            attr = getattr(hook, name)
        except AttributeError:
            continue
        else:
            assert isinstance(attr, types), \
                "Unexpected type '{}' for hook attribute '{}'".format(type(attr).__name__, name)


def test_hook_doc(hook):
    if hook.type == "command" and hook.doc:
        assert DOC_RE.match(hook.doc), \
            "Invalid docstring '{}' format for command hook".format(hook.doc)


def test_hook_args(hook):
    bot = MockBot()
    if hook.type in ("irc_raw", "perm_check", "periodic", "on_start", "on_stop", "event", "on_connect", "sieve"):
        event = Event(bot=bot)
    elif hook.type == "command":
        event = CommandEvent(bot=bot, hook=hook, text="", triggered_command="", cmd_prefix='.')
    elif hook.type == "regex":
        event = RegexEvent(bot=bot, hook=hook, match=None)
    elif hook.type.startswith("on_cap"):
        event = CapEvent(bot=bot, cap="")
    elif hook.type == "post_hook":
        event = PostHookEvent(bot=bot)
    elif hook.type == "irc_out":
        event = IrcOutEvent(bot=bot)
    else:
        assert False, "Unhandled hook type '{}' in tests".format(hook.type)

    populate_args(hook.function, event)


def test_coroutine_hooks(hook):
    if inspect.isgeneratorfunction(hook.function):
        assert asyncio.iscoroutinefunction(hook.function), \
            "Non-coroutine generator function used for a hook. This is most liekly due to incorrect ordering of the hook/coroutine decorators."


def test_hook_lock(hook):
    if hook.single_thread:
        assert isinstance(hook.lock, asyncio.Lock)
