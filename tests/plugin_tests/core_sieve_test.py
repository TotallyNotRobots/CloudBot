from typing import Optional
from unittest.mock import MagicMock

import pytest

from cloudbot.event import CommandEvent, RegexEvent
from cloudbot.util.tokenbucket import TokenBucket
from plugins.core import core_sieve


# noinspection PyUnusedFunction
@pytest.fixture(autouse=True)
def reset_buckets() -> None:
    """
    Clear bucket data after a test
    """
    try:
        yield
    finally:
        core_sieve.buckets.clear()


def test_rate_limit_command() -> None:
    conn = MagicMock()
    conn.name = "foobarconn"
    conn.config = {}
    conn.bot = MagicMock()

    hook = MagicMock()
    hook.type = "command"
    event = CommandEvent(
        text="bar",
        cmd_prefix=".",
        triggered_command="foo",
        hook=hook,
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )
    for _ in range(3):
        res = core_sieve.rate_limit(event.bot, event, event.hook)
        assert res is event

    res = core_sieve.rate_limit(event.bot, event, event.hook)
    assert res is None


def test_rate_limit_regex() -> None:
    conn = MagicMock()
    conn.name = "foobarconn"
    conn.config = {}
    conn.bot = MagicMock()

    hook = MagicMock()
    hook.type = "regex"
    event = RegexEvent(
        hook=hook,
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
        match=MagicMock(),
    )
    for _ in range(3):
        res = core_sieve.rate_limit(event.bot, event, event.hook)
        assert res is event

    res = core_sieve.rate_limit(event.bot, event, event.hook)
    assert res is None


def test_task_clear() -> None:
    core_sieve.buckets["a"] = bucket = TokenBucket(10, 2)
    bucket.timestamp = 0
    assert len(core_sieve.buckets) == 1
    core_sieve.task_clear()
    assert len(core_sieve.buckets) == 0


@pytest.mark.parametrize(
    "config,allowed",
    [
        ({"foo": {"allow-except": ["#foo"]}}, False),
        ({"foo": {"deny-except": ["#bar"]}}, False),
        ({"foo": {"deny-except": ["#foo"]}}, True),
        ({"foo": {"allow-except": ["#bar"]}}, True),
        ({"bar": {"deny-except": ["#bar"]}}, True),
        ({"foo": {"allow-except": []}}, True),
        ({"foo": {"deny-except": []}}, False),
    ],
)
def test_check_acls(config, allowed) -> None:
    event = make_command_event()
    event.conn.config["acls"] = config
    res = core_sieve.check_acls(event.bot, event, event.hook)
    if allowed:
        assert res is event
    else:
        assert res is None


def test_check_acls_no_chan() -> None:
    event = make_command_event(chan=None)
    assert core_sieve.check_acls(event.bot, event, event.hook) is event


@pytest.mark.asyncio()
async def test_permissions() -> None:
    event = make_command_event()
    event.hook.permissions = ["admin"]

    event.has_permission = perm = MagicMock()
    res = await core_sieve.perm_sieve(event.bot, event, event.hook)
    assert res is event

    perm.return_value = False
    res = await core_sieve.perm_sieve(event.bot, event, event.hook)
    assert res is None


def make_command_event(chan: Optional[str] = "#foo") -> CommandEvent:
    conn = MagicMock()
    conn.name = "foobarconn"
    conn.config = {}
    conn.bot = MagicMock()

    hook = MagicMock()
    hook.type = "command"
    hook.function_name = "foo"
    event = CommandEvent(
        text="bar",
        cmd_prefix=".",
        triggered_command="foo",
        hook=hook,
        bot=conn.bot,
        conn=conn,
        channel=chan,
        nick="foobaruser",
        user="user",
        host="host",
    )
    return event


def test_disabled():
    event = make_command_event()
    event.conn.config["disabled_commands"] = [event.triggered_command]
    assert core_sieve.check_disabled(event.bot, event, event.hook) is None
    event.conn.config["disabled_commands"] = ["random"]
    assert core_sieve.check_disabled(event.bot, event, event.hook) is event
    event.conn.config["disabled_commands"] = []
    assert core_sieve.check_disabled(event.bot, event, event.hook) is event
