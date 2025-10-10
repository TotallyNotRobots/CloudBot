import asyncio
from unittest.mock import MagicMock, call

import pytest

from cloudbot.event import CapEvent
from plugins.core import sasl
from tests.util.mock_conn import MockConn


def test_sasl_available_enabled():
    event = CapEvent(
        cap="sasl",
        cap_param=None,
        conn=MockConn(),
    )
    event.conn.config = {"sasl": {"enabled": True}}
    assert sasl.sasl_available(event.conn) is True


def test_sasl_available_disabled():
    event = CapEvent(
        cap="sasl",
        cap_param=None,
        conn=MockConn(),
    )
    event.conn.config = {"sasl": {"enabled": False}}
    assert sasl.sasl_available(event.conn) is False


def test_sasl_available_no_config():
    event = CapEvent(
        cap="sasl",
        cap_param=None,
        conn=MockConn(),
    )
    event.conn.config = {}
    assert sasl.sasl_available(event.conn) is False


@pytest.mark.asyncio
async def test_sasl_ack_plain():
    event = CapEvent(
        cap="sasl",
        cap_param=None,
        conn=MockConn(loop=asyncio.get_event_loop()),
    )
    event.conn.memory = {}
    event.conn.config = {
        "sasl": {
            "enabled": True,
            "mechanism": "PLAIN",
            "user": "test_user",
            "pass": "test_pass",
        }
    }

    auth_string = "dGVzdF91c2VyAHRlc3RfdXNlcgB0ZXN0X3Bhc3M="

    def cmd_handler(command, *args):
        if command == "AUTHENTICATE" and args == ("PLAIN",):
            asyncio.ensure_future(sasl.auth("AUTHENTICATE", event.conn, ["+"]))
        elif command == "AUTHENTICATE" and args == (auth_string,):
            asyncio.ensure_future(sasl.sasl_numerics("903", event.conn))
        else:  # pragma: no cover
            raise ValueError(f"Unexpected command {command} with args {args}")

    event.conn.cmd = MagicMock(side_effect=cmd_handler)
    await sasl.sasl_ack(event.conn)
    assert event.conn.cmd.mock_calls == [
        call("AUTHENTICATE", "PLAIN"),
        call("AUTHENTICATE", auth_string),
    ]
