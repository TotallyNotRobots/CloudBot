import importlib
from unittest.mock import MagicMock

from cloudbot import hook, plugin_hooks
from cloudbot.event import CommandEvent
from plugins import urban
from tests.util import wrap_hook_response


def test_urban(mock_requests, reset_database):
    mock_requests.add(
        "GET",
        "http://api.urbandictionary.com/v0/define?term=foo",
        match_querystring=True,
        json={
            "list": [
                {
                    "definition": "foobar",
                    "permalink": "http://foo.urbanup.com/1",
                }
            ]
        },
    )
    importlib.reload(urban)
    func_hook = hook.get_hooks(urban.urban)["command"]
    plugin = MagicMock()
    cmd_hook = plugin_hooks.hook_name_to_plugin(func_hook.type)(
        plugin, func_hook
    )
    event = CommandEvent(
        channel="#foo",
        text="foo",
        triggered_command="urban",
        cmd_prefix=".",
        hook=cmd_hook,
        nick="foonick",
        conn=MagicMock(),
    )
    res = wrap_hook_response(urban.urban, event)
    assert res == [("return", "[1/1] foobar - http://foo.urbanup.com/1")]
