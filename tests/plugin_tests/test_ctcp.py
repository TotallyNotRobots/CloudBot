import importlib
from unittest.mock import MagicMock

import pytest

from cloudbot.event import Event
from plugins.core import core_ctcp
from tests.util import wrap_hook_response


@pytest.mark.parametrize(
    "text,output",
    [
        ("VERSION", "VERSION {}".format(core_ctcp.VERSION)),
        ("PING 1", "PING 1"),
        ("TIME", "TIME Thu Aug 22 19:14:36 2019"),
    ],
)
def test_ctcp_handler(text, output, freeze_time):
    importlib.reload(core_ctcp)
    event = Event(
        irc_ctcp_text=text, conn=MagicMock(), bot=MagicMock(), nick="foo"
    )
    res = wrap_hook_response(core_ctcp.ctcp_version, event)
    assert res == [("message", ("foo", "\1{}\1".format(output)))]
