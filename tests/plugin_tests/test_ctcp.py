from unittest.mock import MagicMock, call

import pytest

from plugins.core import core_ctcp


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text,out",
    [
        (
            "VERSION",
            "\x01VERSION gonzobot a fork of Cloudbot 1.3.0 - https://snoonet.org/gonzobot\x01",
        ),
        ("PING 1", "\x01PING 1\x01"),
        ("TIME", "\x01TIME Thu Aug 22 13:14:36 2019\x01"),
    ],
)
async def test_ctcp_handler(text, out, freeze_time):
    event = MagicMock()
    res = await core_ctcp.ctcp_version(event.notice, text)
    assert res is None
    assert event.mock_calls == [call.notice(out)]
