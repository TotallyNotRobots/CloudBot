import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from irclib.parser import CapList, ParamList

from cloudbot import hook
from cloudbot.event import Event
from cloudbot.plugin import PluginManager
from cloudbot.util import async_util
from plugins.core import cap
from tests.util.mock_module import MockModule


@pytest.fixture()
def patch_import_module():
    with patch("importlib.import_module") as mocked:
        yield mocked


@pytest.mark.asyncio()
async def test_cap_req(patch_import_module):
    caps = [
        "some-cap",
        "another-cap",
        "a.vendor/cap",
        "a-cap=with-value",
        "a.vendor/cap=with-value",
    ]
    cap_names = [s.split("=")[0] for s in caps]

    params = ParamList.parse("* LS :" + " ".join(caps))
    event = Event(irc_paramlist=params, bot=MagicMock(), conn=MagicMock())
    event.conn.loop = event.bot.loop = asyncio.get_event_loop()
    event.bot.config = {}
    event.conn.type = "irc"
    event.bot.base_dir = Path(".").resolve()
    event.bot.plugin_manager = manager = PluginManager(event.bot)

    called = False

    def func():
        nonlocal called
        called = True
        return True

    for c in cap_names:
        func = hook.on_cap_available(c)(func)

    patch_import_module.return_value = MockModule(func=func)
    await manager.load_plugin("plugins/test.py")

    event.conn.memory = {}

    cap.send_cap_ls(event.conn)
    event.conn.cmd.assert_called_with("CAP", "LS", "302")

    event.conn.cmd.reset_mock()

    calls = []

    def cmd(cmd, subcmd, *args):
        calls.append((cmd, subcmd) + args)
        p = ParamList.parse("* ACK :" + " ".join(args))
        cmd_event = Event(irc_paramlist=p, bot=event.bot, conn=event.conn)
        async_util.wrap_future(cap.on_cap(p, cmd_event), loop=event.loop)

    with patch.object(event.conn, "cmd", new=cmd):
        res = await cap.on_cap(params, event)
        assert called
        assert res is None

    caps = event.conn.memory["server_caps"]
    assert caps == {c: True for c in cap_names}

    assert calls == [("CAP", "REQ", c) for c in cap_names]


@pytest.mark.asyncio()
async def test_cap_new(patch_import_module):
    caps = [
        "some-cap",
        "another-cap",
        "a.vendor/cap",
        "a-cap=with-value",
        "a.vendor/cap=with-value",
    ]
    cap_names = [s.split("=")[0] for s in caps]
    params = ParamList.parse("* NEW :" + " ".join(cap_names))
    event = Event(irc_paramlist=params, bot=MagicMock(), conn=MagicMock())
    event.conn.loop = event.bot.loop = asyncio.get_event_loop()
    event.bot.config = {}
    event.conn.type = "irc"
    event.bot.base_dir = Path(".").resolve()
    event.bot.plugin_manager = manager = PluginManager(event.bot)

    called = False

    def func():
        nonlocal called
        called = True
        return True

    for c in cap_names:
        func = hook.on_cap_available(c)(func)

    patch_import_module.return_value = MockModule(func=func)
    await manager.load_plugin("plugins/test.py")
    event.conn.memory = {"available_caps": CapList(), "cap_queue": {}}

    calls = []

    def cmd(cmd, subcmd, *args):
        calls.append((cmd, subcmd) + args)
        p = ParamList.parse("* ACK :" + " ".join(args))
        cmd_event = Event(irc_paramlist=p, bot=event.bot, conn=event.conn)
        async_util.wrap_future(cap.on_cap(p, cmd_event), loop=event.loop)

    with patch.object(event.conn, "cmd", new=cmd):
        res = await cap.on_cap(params, event)
        assert called
        assert res is None

    assert calls == [
        ("CAP", "REQ", "some-cap"),
        ("CAP", "REQ", "another-cap"),
        ("CAP", "REQ", "a.vendor/cap"),
        ("CAP", "REQ", "a-cap"),
        ("CAP", "REQ", "a.vendor/cap"),
    ]


@pytest.mark.asyncio()
async def test_cap_nak(patch_import_module):
    caps = [
        "some-cap",
        "another-cap",
        "a.vendor/cap",
        "a-cap=with-value",
        "a.vendor/cap=with-value",
    ]
    cap_names = [s.split("=")[0] for s in caps]
    params = ParamList.parse("* NAK :" + " ".join(cap_names))
    event = Event(irc_paramlist=params, bot=MagicMock(), conn=MagicMock())
    event.conn.loop = event.bot.loop = asyncio.get_event_loop()
    event.bot.config = {}
    event.conn.type = "irc"
    event.bot.base_dir = Path(".").resolve()
    event.bot.plugin_manager = manager = PluginManager(event.bot)

    called = False

    def func():
        ...

    for c in cap_names:
        func = hook.on_cap_ack(c)(func)

    patch_import_module.return_value = MockModule(func=func)
    await manager.load_plugin("plugins/test.py")
    fut = async_util.create_future()
    event.conn.memory = {
        "available_caps": CapList(),
        "cap_queue": {"some-cap": fut},
    }

    res = await cap.on_cap(params, event)
    assert not called
    assert (await fut) is False
    assert res is None


@pytest.mark.asyncio()
async def test_cap_foo(patch_import_module):
    params = ParamList.parse("* FOO :bar")
    event = Event(irc_paramlist=params, bot=MagicMock(), conn=MagicMock())
    event.conn.loop = event.bot.loop = asyncio.get_event_loop()
    event.bot.config = {}
    event.conn.type = "irc"
    event.bot.base_dir = Path(".").resolve()
    event.bot.plugin_manager = PluginManager(event.bot)
    event.conn.memory = {"available_caps": CapList(), "cap_queue": {}}

    res = await cap.on_cap(params, event)
    assert res is None


@pytest.mark.asyncio()
async def test_cap_del(patch_import_module):
    params = ParamList.parse("* DEL :bar")
    event = Event(irc_paramlist=params, bot=MagicMock(), conn=MagicMock())
    event.conn.loop = event.bot.loop = asyncio.get_event_loop()
    event.bot.config = {}
    event.conn.type = "irc"
    event.bot.base_dir = Path(".").resolve()
    event.bot.plugin_manager = PluginManager(event.bot)
    event.conn.memory = {"available_caps": CapList(), "cap_queue": {}}

    res = await cap.on_cap(params, event)
    assert res is None
    assert event.conn.memory == {
        "available_caps": [],
        "cap_queue": {},
        "server_caps": {"bar": False},
    }


@pytest.mark.asyncio()
async def test_cap_list():
    caps = [
        "some-cap",
        "another-cap",
        "a.vendor/cap",
        "a-cap=with-value",
        "a.vendor/cap=with-value",
    ]
    cap_names = [s.split("=")[0] for s in caps]
    params = ParamList.parse("* LIST :" + " ".join(cap_names))
    event = Event(irc_paramlist=params, bot=MagicMock(), conn=MagicMock())
    event.conn.loop = event.bot.loop = asyncio.get_event_loop()
    event.bot.config = {}
    event.conn.type = "irc"
    event.bot.base_dir = Path(".").resolve()
    event.bot.plugin_manager = PluginManager(event.bot)

    called = False

    event.conn.memory = {"available_caps": CapList(), "cap_queue": {}}

    res = await cap.on_cap(params, event)
    assert not called
    assert res is None
