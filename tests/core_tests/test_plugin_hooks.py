"""
Validates all hook registrations in all plugins
"""
import importlib
import string
from numbers import Number
from pathlib import Path

import pytest
from sqlalchemy import MetaData

from cloudbot.hook import Action
from cloudbot.plugin import Plugin, Hook


def patch_hook_init(self, _type, plugin, func_hook):
    self.original_init(_type, plugin, func_hook)

    assert not func_hook.kwargs, \
        "Unknown arguments '{}' passed during registration of hook '{}'".format(func_hook.kwargs, self.function_name)


def gather_plugins():
    plugin_dir = Path("plugins")
    path_list = plugin_dir.rglob("[!_]*.py")
    return path_list


def load_plugin(plugin_path, monkeypatch):
    monkeypatch.setattr('cloudbot.plugin.Hook.original_init', Hook.__init__, raising=False)
    monkeypatch.setattr('cloudbot.plugin.Hook.__init__', patch_hook_init)

    monkeypatch.setattr('cloudbot.util.database.metadata', MetaData())

    path = Path(plugin_path)
    file_path = path.resolve()
    file_name = file_path.name
    # Resolve the path relative to the current directory
    plugin_path = file_path.relative_to(Path().resolve())
    title = '.'.join(plugin_path.parts[1:]).rsplit('.', 1)[0]

    module_name = "plugins.{}".format(title)

    plugin_module = importlib.import_module(module_name)

    return Plugin(str(file_path), file_name, title, plugin_module)


def pytest_generate_tests(metafunc):
    if 'plugin_path' in metafunc.fixturenames:
        param_list = (pytest.param(path, id=path) for path in gather_plugins())
        metafunc.parametrize('plugin_path', param_list)


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


def test_plugin(plugin_path, monkeypatch):
    plugin = load_plugin(plugin_path, monkeypatch)
    for hooks in plugin.hooks.values():
        for hook in hooks:
            _test_hook(hook)


def _test_hook(hook):
    assert 'async' not in hook.required_args, "Use of deprecated function Event.async"
    for name, types in HOOK_ATTR_TYPES.items():
        try:
            attr = getattr(hook, name)
        except AttributeError:
            continue
        else:
            assert isinstance(attr, types), \
                "Unexpected type '{}' for hook attribute '{}'".format(type(attr).__name__, name)

    if hook.type == "command" and hook.doc:
        assert hook.doc[:1] not in "." + string.ascii_letters,\
            "Invalid docstring '{}' format for command hook".format(hook.doc)
