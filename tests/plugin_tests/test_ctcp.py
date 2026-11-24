from unittest.mock import MagicMock, call

import pytest

import cloudbot
from plugins.core import core_ctcp
from tests.util import with_frozen_time


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "out"),
    [
        (
            "VERSION",
            f"\x01VERSION gonzobot a fork of Cloudbot {cloudbot.__version__} - https://snoonet.org/gonzobot\x01",
        ),
        ("PING 1", "\x01PING 1\x01"),
        ("TIME", "\x01TIME Thu Aug 22 13:14:36 2019\x01"),
    ],
)
@with_frozen_time()
async def test_ctcp_handler(text, out) -> None:
    event = MagicMock()
    res = await core_ctcp.ctcp_version(event.notice, text)
    assert res is None
    assert event.mock_calls == [call.notice(out)]
