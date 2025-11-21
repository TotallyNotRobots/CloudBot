from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import call, patch

import pytest
from irclib.parser import ParamList

from cloudbot import hook
from cloudbot.event import Event
from plugins.core import cap
from tests.util.mock_irc_client import MockIrcClient
from tests.util.mock_module import MockModule

if TYPE_CHECKING:
    from tests.util.mock_bot import MockBot


@pytest.mark.asyncio()
async def test_cap_req(patch_import_module, mock_bot: MockBot) -> None:
    conn = MockIrcClient(bot=mock_bot)
    caps = [
        "some-cap",
        "another-cap",
        "a.vendor/cap",
        "a-cap=with-value",
        "a.vendor/cap=with-value",
    ]
    cap_names = [s.split("=")[0] for s in caps]

    params = ParamList.parse(f"* LS :{' '.join(caps)}")
    event = Event(
        irc_paramlist=params,
        bot=mock_bot,
        conn=conn,
    )

    called = False

    def func() -> bool:
        nonlocal called
        called = True
        return True

    for c in cap_names:
        func = hook.on_cap_available(c)(func)

    patch_import_module.return_value = MockModule(func=func)
    await mock_bot.get_plugin_manager().load_plugin(
        mock_bot.base_dir / "plugins" / "test.py"
    )

    cap.send_cap_ls(event.conn)

    assert conn.mock_calls() == [call.send("CAP LS 302")]

    calls = []

    def cmd(cmd, subcmd, *args) -> None:
        calls.append((cmd, subcmd) + args)
        p = ParamList.parse(f"* ACK :{' '.join(args)}")
        cmd_event = Event(
            irc_paramlist=p,
            bot=event.bot,
            conn=event.conn,
        )
        asyncio.ensure_future(cap.on_cap(p, cmd_event), loop=event.loop)

    with patch.object(event.conn, "cmd", new=cmd):
        res = await cap.on_cap(params, event)
        assert called
        assert res is None

    info = cap.CapInfoExt.ensure(event.conn)
    assert info.server_caps == {c: True for c in cap_names}

    assert calls == [("CAP", "REQ", c) for c in cap_names]
    assert conn.mock_calls() == [call.send("CAP LS 302"), call.send("CAP END")]
