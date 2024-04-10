from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from cloudbot.event import CommandEvent
from plugins.core import optout
from tests.util import wrap_hook_response_async
from tests.util.mock_db import MockDB


def test_conn_case():
    conn_list = optout.optout_cache["TestConnection"]

    assert optout.get_conn_optouts("TestConnection") is conn_list
    assert optout.get_conn_optouts("testconnection") is conn_list
    assert optout.get_conn_optouts("testconnection1") is not conn_list

    conn_list = optout.optout_cache["testconnection"]

    assert optout.get_conn_optouts("TestConnection") is conn_list
    assert optout.get_conn_optouts("testconnection") is conn_list
    assert optout.get_conn_optouts("testconnection1") is not conn_list


def test_ignore_core():
    bot = MagicMock()
    event = MagicMock()
    _hook = MagicMock()

    _hook.plugin.title = "core.optout"
    _hook.function_name = "optout"

    event.chan = "#test"
    conn = event.conn

    conn.name = "test"

    opt = optout.OptOut("#test", "*", False)

    with patch.dict(optout.optout_cache, clear=True, test=[opt]):
        res = optout.optout_sieve(bot, event, _hook)
        assert res is event


def test_match():
    bot = MagicMock()
    event = MagicMock()
    _hook = MagicMock()

    _hook.plugin.title = "test"
    _hook.function_name = "optout"

    event.chan = "#test"
    conn = event.conn

    conn.name = "test"

    opt = optout.OptOut("#test", "*", False)

    with patch.dict(optout.optout_cache, clear=True, test=[opt]):
        res = optout.optout_sieve(bot, event, _hook)
        assert res is None


def test_get_first_matching_optout(mock_db):
    optout.optout_table.create(mock_db.engine)
    mock_db.load_data(
        optout.optout_table,
        [
            {
                "network": "my_net",
                "chan": "#*",
                "hook": "my.*",
                "allow": False,
            },
            {
                "network": "my_net",
                "chan": "#my*",
                "hook": "*.*",
                "allow": True,
            },
        ],
    )

    optout.load_cache(mock_db.session())

    assert (
        optout.get_first_matching_optout("my_net", "#my_chan", "my.hook").allow
        is True
    )


def test_optout_match():
    assert optout.OptOut(
        channel="#foo*", hook_pattern="foo.*", allow=True
    ).match("#foobar", "foo.bar")


def test_optout_compare():
    with pytest.raises(TypeError):
        assert (
            optout.OptOut(channel="#foo*", hook_pattern="foo.*", allow=True) > 5  # type: ignore[operator]
        )


def test_optout_eq_other():
    assert optout.OptOut(channel="#foo*", hook_pattern="foo.*", allow=True) != 5


def test_optout_equals():
    args = {"channel": "#foo", "hook_pattern": "foo", "allow": True}
    assert optout.OptOut(**args) == optout.OptOut(**args)


def test_optout_sort():
    optouts = [
        optout.OptOut(channel="#aaa", hook_pattern="test", allow=True),
        optout.OptOut(channel="#aaa", hook_pattern="test*", allow=True),
        optout.OptOut(channel="#aaa", hook_pattern="tes*", allow=True),
        optout.OptOut(channel="#aaa", hook_pattern="te*", allow=True),
        optout.OptOut(channel="#aa", hook_pattern="test", allow=True),
    ]

    assert sorted(optouts) == [
        optout.OptOut(channel="#aa", hook_pattern="test", allow=True),
        optout.OptOut(channel="#aaa", hook_pattern="te*", allow=True),
        optout.OptOut(channel="#aaa", hook_pattern="tes*", allow=True),
        optout.OptOut(channel="#aaa", hook_pattern="test", allow=True),
        optout.OptOut(channel="#aaa", hook_pattern="test*", allow=True),
    ]


def test_exact_override():
    net = "my_net"
    channel = "#foobar"
    hook = "my.hook"
    optouts = {
        net: [
            optout.OptOut(
                channel="#foo*",
                hook_pattern="my.*",
                allow=False,
            ),
            optout.OptOut(
                channel="#foobar",
                hook_pattern="my.*",
                allow=True,
            ),
            optout.OptOut(
                channel="#fooba*",
                hook_pattern="my.*",
                allow=False,
            ),
            optout.OptOut(
                channel="#foobar*",
                hook_pattern="my.*",
                allow=False,
            ),
        ]
    }

    for opts in optouts.values():
        opts.sort(reverse=True)

    with patch.dict(optout.optout_cache, clear=True, values=optouts):
        assert (
            optout.get_first_matching_optout(net, channel, hook).allow is True
        )


async def test_check_channel_permissions():
    event = MagicMock()
    event.chan = "#foo"
    event.check_permissions = AsyncMock(return_value=True)
    res = await optout.check_channel_permissions(
        event, "#bar", "botcontrol", "staff"
    )
    assert res


def test_get_global_optouts():
    optouts = {
        "net2": [
            optout.OptOut(
                channel="#foo*",
                hook_pattern="my.*",
                allow=True,
            ),
        ],
        "net": [
            optout.OptOut(
                "#baz",
                hook_pattern="my.hook",
                allow=True,
            ),
            optout.OptOut(
                channel="#foo*",
                hook_pattern="my.*",
                allow=False,
            ),
            optout.OptOut(
                channel="#foobar",
                hook_pattern="my.*",
                allow=True,
            ),
            optout.OptOut(
                channel="#fooba*",
                hook_pattern="my.*",
                allow=False,
            ),
            optout.OptOut(
                channel="#foobar*",
                hook_pattern="my.*",
                allow=False,
            ),
        ],
    }

    for opts in optouts.values():
        opts.sort(reverse=True)

    with patch.dict(optout.optout_cache, clear=True, values=optouts):
        assert optout.get_channel_optouts("net", None) == [
            optout.OptOut(
                channel="#foobar",
                hook_pattern="my.*",
                allow=True,
            ),
            optout.OptOut(
                channel="#foobar*",
                hook_pattern="my.*",
                allow=False,
            ),
            optout.OptOut(
                channel="#fooba*",
                hook_pattern="my.*",
                allow=False,
            ),
            optout.OptOut(
                channel="#foo*",
                hook_pattern="my.*",
                allow=False,
            ),
            optout.OptOut(
                "#baz",
                hook_pattern="my.hook",
                allow=True,
            ),
        ]


def test_match_optout():
    optouts = {
        "net2": [
            optout.OptOut(
                channel="#foo*",
                hook_pattern="my.*",
                allow=True,
            ),
        ],
        "net": [
            optout.OptOut(
                channel="#other",
                hook_pattern="my.hook",
                allow=True,
            ),
            optout.OptOut(
                "#baz",
                hook_pattern="my.hook",
                allow=True,
            ),
            optout.OptOut(
                channel="#foo*",
                hook_pattern="my.*",
                allow=False,
            ),
            optout.OptOut(
                channel="#foobar",
                hook_pattern="my.*",
                allow=True,
            ),
            optout.OptOut(
                channel="#fooba*",
                hook_pattern="my.*",
                allow=False,
            ),
            optout.OptOut(
                channel="#foobar*",
                hook_pattern="my.*",
                allow=False,
            ),
        ],
    }

    for opts in optouts.values():
        opts.sort(reverse=True)

    with patch.dict(optout.optout_cache, clear=True, values=optouts):
        assert (
            optout.get_first_matching_optout(
                "my_other_net", "#foobar", "my.hook"
            )
            is None
        )
        assert (
            optout.get_first_matching_optout("net", "#chan", "my.hook") is None
        )
        assert (
            optout.get_first_matching_optout(
                "net", "#foobar", "some.other_hook"
            )
            is None
        )
        assert (
            optout.get_first_matching_optout("net", "#foobar", "my.hook").allow
            is True
        )


def test_format():
    optouts = [
        optout.OptOut(
            channel="#other",
            hook_pattern="my.hook",
            allow=True,
        ),
        optout.OptOut(
            "#baz",
            hook_pattern="my.hook",
            allow=True,
        ),
        optout.OptOut(
            channel="#foo*",
            hook_pattern="my.*",
            allow=False,
        ),
        optout.OptOut(
            channel="#foobar",
            hook_pattern="my.*",
            allow=True,
        ),
        optout.OptOut(
            channel="#fooba*",
            hook_pattern="my.*",
            allow=False,
        ),
        optout.OptOut(
            channel="#foobar*",
            hook_pattern="my.*",
            allow=False,
        ),
    ]

    assert (
        optout.format_optout_list(optouts)
        == """\
| Channel Pattern | Hook Pattern | Allowed |
| --------------- | ------------ | ------- |
| #other          | my.hook      | true    |
| #baz            | my.hook      | true    |
| #foo*           | my.*         | false   |
| #foobar         | my.*         | true    |
| #fooba*         | my.*         | false   |
| #foobar*        | my.*         | false   |"""
    )


class TestSetOptOut:
    async def test_cmd(self, mock_db: MockDB, mock_bot) -> None:
        with mock_db.session() as session:
            optout.optout_table.create(mock_db.engine)
            optout.load_cache(session)
            conn = MagicMock()
            conn.configure_mock(name="net")
            event = CommandEvent(
                nick="nick",
                channel="#chan",
                conn=conn,
                bot=mock_bot,
                hook=MagicMock(),
                text="foo.*",
                triggered_command="optout",
                cmd_prefix=".",
            )
            event.db = session
            has_perm = MagicMock()
            has_perm.return_value = True
            with patch.object(event, "has_permission", has_perm):
                res = await wrap_hook_response_async(optout.optout, event)

            assert res == [
                ("return", "Disabled hooks matching foo.* in #chan.")
            ]
            assert conn.mock_calls == []
            assert has_perm.mock_calls == [call("op", notice=True)]
            assert mock_db.get_data(optout.optout_table) == [
                ("net", "#chan", "foo.*", False)
            ]

    def test_add(self, mock_db: MockDB):
        with mock_db.session() as session:
            optout.optout_table.create(mock_db.engine)
            optout.load_cache(session)
            optout.set_optout(session, "net", "#chan", "my.hook", True)

            assert mock_db.get_data(optout.optout_table) == [
                ("net", "#chan", "my.hook", True)
            ]

    def test_update(self, mock_db: MockDB):
        with mock_db.session() as session:
            optout.optout_table.create(mock_db.engine)
            mock_db.load_data(
                optout.optout_table,
                [
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "my.hook",
                        "allow": False,
                    }
                ],
            )

            optout.load_cache(session)

            assert mock_db.get_data(optout.optout_table) == [
                ("net", "#chan", "my.hook", False)
            ]

            optout.set_optout(session, "net", "#chan", "my.hook", True)

            assert mock_db.get_data(optout.optout_table) == [
                ("net", "#chan", "my.hook", True)
            ]


class TestDelOptOut:
    async def test_del_cmd(self, mock_db: MockDB, mock_bot) -> None:
        with mock_db.session() as session:
            optout.optout_table.create(mock_db.engine)
            mock_db.load_data(
                optout.optout_table,
                [
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "foo.*",
                        "allow": False,
                    },
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "foo1.*",
                        "allow": False,
                    },
                    {
                        "network": "net1",
                        "chan": "#chan",
                        "hook": "foo.*",
                        "allow": False,
                    },
                    {
                        "network": "net",
                        "chan": "#chan1",
                        "hook": "foo.*",
                        "allow": False,
                    },
                ],
            )
            optout.load_cache(session)
            conn = MagicMock()
            conn.configure_mock(name="net")
            event = CommandEvent(
                nick="nick",
                channel="#chan",
                conn=conn,
                bot=mock_bot,
                hook=MagicMock(),
                text="foo.*",
                triggered_command="deloptout",
                cmd_prefix=".",
            )
            event.db = session
            has_perm = MagicMock()
            has_perm.return_value = True
            with patch.object(event, "has_permission", has_perm):
                res = await wrap_hook_response_async(optout.deloptout, event)

            assert res == [
                ("return", "Deleted optout 'foo.*' in channel '#chan'.")
            ]
            assert conn.mock_calls == []
            assert has_perm.mock_calls == [call("op", notice=True)]
            assert mock_db.get_data(optout.optout_table) == [
                ("net", "#chan", "foo1.*", False),
                ("net1", "#chan", "foo.*", False),
                ("net", "#chan1", "foo.*", False),
            ]

    def test_del_no_match(self, mock_db: MockDB):
        with mock_db.session() as session:
            optout.optout_table.create(mock_db.engine)
            assert (
                optout.del_optout(session, "net", "#chan", "my.hook") is False
            )

    def test_del(self, mock_db: MockDB):
        with mock_db.session() as session:
            optout.optout_table.create(mock_db.engine)
            mock_db.load_data(
                optout.optout_table,
                [
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "my.hook",
                        "allow": False,
                    }
                ],
            )

            assert mock_db.get_data(optout.optout_table) == [
                ("net", "#chan", "my.hook", False)
            ]

            assert optout.del_optout(session, "net", "#chan", "my.hook") is True

            assert mock_db.get_data(optout.optout_table) == []


class TestClearOptOut:
    async def test_clear_cmd(self, mock_db: MockDB, mock_bot) -> None:
        with mock_db.session() as session:
            optout.optout_table.create(mock_db.engine)
            mock_db.load_data(
                optout.optout_table,
                [
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "foo.*",
                        "allow": False,
                    },
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "foo1.*",
                        "allow": False,
                    },
                    {
                        "network": "net1",
                        "chan": "#chan",
                        "hook": "foo.*",
                        "allow": False,
                    },
                    {
                        "network": "net",
                        "chan": "#chan1",
                        "hook": "foo.*",
                        "allow": False,
                    },
                ],
            )
            optout.load_cache(session)
            conn = MagicMock()
            conn.configure_mock(name="net")
            event = CommandEvent(
                nick="nick",
                channel="#chan",
                conn=conn,
                bot=mock_bot,
                hook=MagicMock(),
                text="",
                triggered_command="clearoptout",
                cmd_prefix=".",
            )
            event.db = session
            has_perm = MagicMock()
            has_perm.return_value = True
            with patch.object(event, "has_permission", has_perm):
                res = await wrap_hook_response_async(optout.clear, event)

            assert res == [("return", "Cleared 2 opt outs from the list.")]
            assert conn.mock_calls == []
            assert has_perm.mock_calls == [call("snoonetstaff", notice=True)]
            assert mock_db.get_data(optout.optout_table) == [
                ("net1", "#chan", "foo.*", False),
                ("net", "#chan1", "foo.*", False),
            ]

    def test_clear_chan(self, mock_db: MockDB):
        with mock_db.session() as session:
            optout.optout_table.create(mock_db.engine)
            mock_db.load_data(
                optout.optout_table,
                [
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "my.hook",
                        "allow": False,
                    },
                    {
                        "network": "othernet",
                        "chan": "#chan",
                        "hook": "my.hook",
                        "allow": False,
                    },
                    {
                        "network": "net",
                        "chan": "#otherchan",
                        "hook": "my.hook",
                        "allow": False,
                    },
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "other.hook",
                        "allow": False,
                    },
                ],
            )

            assert len(mock_db.get_data(optout.optout_table)) == 4

            assert optout.clear_optout(session, "net", "#chan") == 2

            assert len(mock_db.get_data(optout.optout_table)) == 2

    def test_clear_conn(self, mock_db: MockDB):
        with mock_db.session() as session:
            optout.optout_table.create(mock_db.engine)
            mock_db.load_data(
                optout.optout_table,
                [
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "my.hook",
                        "allow": False,
                    },
                    {
                        "network": "othernet",
                        "chan": "#chan",
                        "hook": "my.hook",
                        "allow": False,
                    },
                    {
                        "network": "net",
                        "chan": "#otherchan",
                        "hook": "my.hook",
                        "allow": False,
                    },
                    {
                        "network": "net",
                        "chan": "#chan",
                        "hook": "other.hook",
                        "allow": False,
                    },
                ],
            )

            assert len(mock_db.get_data(optout.optout_table)) == 4

            assert optout.clear_optout(session, "net") == 3

            assert len(mock_db.get_data(optout.optout_table)) == 1
