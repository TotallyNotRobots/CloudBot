from re import Match
from unittest.mock import MagicMock

import pytest

from cloudbot.client import Client
from cloudbot.event import CommandEvent, Event, RegexEvent
from cloudbot.plugin import Plugin
from cloudbot.plugin_hooks import CommandHook, EventHook, RegexHook
from plugins.core import regex_chans
from tests.util import wrap_hook_response
from tests.util.mock_conn import MockClient
from tests.util.mock_db import MockDB


@pytest.fixture()
def clear_cache():
    regex_chans.status_cache.clear()
    yield
    regex_chans.status_cache.clear()


pytestmark = pytest.mark.usefixtures("clear_cache")


def test_status_new(mock_db: MockDB):
    regex_chans.table.create(mock_db.engine)
    with mock_db.session() as session:
        mock_db.load_data(regex_chans.table, [])

        regex_chans.load_cache(session)

        regex_chans.set_status(session, "net", "#chan", True)

        assert mock_db.get_data(regex_chans.table) == [
            ("net", "#chan", "ENABLED")
        ]

        assert regex_chans.status_cache == {("net", "#chan"): True}


def test_status_existing(mock_db: MockDB):
    regex_chans.table.create(mock_db.engine)
    with mock_db.session() as session:
        mock_db.load_data(
            regex_chans.table,
            [{"connection": "net", "channel": "#chan", "status": "DISABLED"}],
        )

        regex_chans.load_cache(session)

        regex_chans.set_status(session, "net", "#chan", True)

        assert mock_db.get_data(regex_chans.table) == [
            ("net", "#chan", "ENABLED")
        ]

        assert regex_chans.status_cache == {("net", "#chan"): True}


def test_delete_status(mock_db: MockDB):
    regex_chans.table.create(mock_db.engine)
    with mock_db.session() as session:
        mock_db.load_data(
            regex_chans.table,
            [{"connection": "net", "channel": "#chan", "status": "DISABLED"}],
        )

        regex_chans.load_cache(session)

        regex_chans.delete_status(session, "net", "#chan")

        assert mock_db.get_data(regex_chans.table) == []

        assert regex_chans.status_cache == {}


def test_listregex(mock_db: MockDB, mock_bot):
    regex_chans.table.create(mock_db.engine)
    with mock_db.session() as session:
        mock_db.load_data(
            regex_chans.table,
            [
                {"connection": "net", "channel": "#chan", "status": "DISABLED"},
                {"connection": "net", "channel": "#chan1", "status": "ENABLED"},
                {
                    "connection": "net",
                    "channel": "#chan2",
                    "status": "DISABLED",
                },
                {
                    "connection": "net",
                    "channel": "#chan3",
                    "status": "DISABLED",
                },
                {
                    "connection": "net1",
                    "channel": "#chan3",
                    "status": "DISABLED",
                },
            ],
        )

        regex_chans.load_cache(session)

        conn = MockClient(bot=mock_bot, name="net")
        assert (
            regex_chans.listregex(conn)
            == "#chan: DISABLED, #chan1: ENABLED, #chan2: DISABLED, #chan3: DISABLED"
        )


class TestRegexStatus:
    def test_current_chan(self, mock_db: MockDB, mock_bot):
        regex_chans.table.create(mock_db.engine)
        with mock_db.session() as session:
            mock_db.load_data(
                regex_chans.table,
                [
                    {
                        "connection": "net",
                        "channel": "#chan",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan1",
                        "status": "ENABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan2",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net1",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                ],
            )

            regex_chans.load_cache(session)

            conn = MockClient(bot=mock_bot, name="net")
            assert (
                regex_chans.regexstatus("", conn, "#chan")
                == "Regex status for #chan: DISABLED"
            )

    def test_other_chan(self, mock_db: MockDB, mock_bot):
        regex_chans.table.create(mock_db.engine)
        with mock_db.session() as session:
            mock_db.load_data(
                regex_chans.table,
                [
                    {
                        "connection": "net",
                        "channel": "#chan",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan1",
                        "status": "ENABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan2",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net1",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                ],
            )

            regex_chans.load_cache(session)

            conn = MockClient(bot=mock_bot, name="net")
            assert (
                regex_chans.regexstatus("#chan1", conn, "#chan")
                == "Regex status for #chan1: ENABLED"
            )

    def test_other_chan_no_prefix(self, mock_db: MockDB, mock_bot):
        regex_chans.table.create(mock_db.engine)
        with mock_db.session() as session:
            mock_db.load_data(
                regex_chans.table,
                [
                    {
                        "connection": "net",
                        "channel": "#chan",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan1",
                        "status": "ENABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan2",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net1",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                ],
            )

            regex_chans.load_cache(session)

            conn = MockClient(bot=mock_bot, name="net")
            assert (
                regex_chans.regexstatus("chan2", conn, "#chan")
                == "Regex status for #chan2: DISABLED"
            )


class TestRegexSieve:
    @pytest.mark.asyncio
    async def test_block_regex_hook(
        self, mock_bot_factory, mock_db: MockDB, caplog
    ):
        mock_bot = mock_bot_factory(db=mock_db)
        regex_chans.table.create(mock_db.engine)
        with mock_db.session() as session:
            mock_db.load_data(
                regex_chans.table,
                [
                    {
                        "connection": "net",
                        "channel": "#chan",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan1",
                        "status": "ENABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan2",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net1",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                ],
            )

            regex_chans.load_cache(session)

            conn = MagicMock()
            conn.configure_mock(name="net")
            conn.mock_add_spec(spec=Client, spec_set=True)

            plugin = MagicMock()
            plugin.configure_mock(title="foo")
            plugin.mock_add_spec(spec=Plugin, spec_set=True)

            hook = MagicMock()
            hook.configure_mock(
                type="regex", plugin=plugin, function_name="my_func"
            )
            hook.mock_add_spec(spec=RegexHook, spec_set=True)

            re_match = MagicMock()
            re_match.mock_add_spec(spec=Match, spec_set=True)

            event = RegexEvent(
                bot=mock_bot,
                conn=conn,
                match=re_match,
                hook=hook,
                channel="#chan",
            )

            res = regex_chans.sieve_regex(mock_bot, event, hook)

            assert hook.mock_calls == []
            assert plugin.mock_calls == []
            assert conn.mock_calls == []
            assert re_match.mock_calls == []

            assert res is None
            assert caplog.messages == ["[net] Denying my_func from #chan"]

    @pytest.mark.asyncio
    async def test_allow_regex_hook(
        self, mock_bot_factory, mock_db: MockDB, caplog
    ):
        mock_bot = mock_bot_factory(db=mock_db)
        regex_chans.table.create(mock_db.engine)
        with mock_db.session() as session:
            mock_db.load_data(
                regex_chans.table,
                [
                    {
                        "connection": "net",
                        "channel": "#chan",
                        "status": "ENABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan1",
                        "status": "ENABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan2",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net1",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                ],
            )

            regex_chans.load_cache(session)

            conn = MagicMock()
            conn.configure_mock(name="net")
            conn.mock_add_spec(spec=Client, spec_set=True)

            plugin = MagicMock()
            plugin.configure_mock(title="foo")
            plugin.mock_add_spec(spec=Plugin, spec_set=True)

            hook = MagicMock()
            hook.configure_mock(
                type="regex", plugin=plugin, function_name="my_func"
            )
            hook.mock_add_spec(spec=RegexHook, spec_set=True)

            re_match = MagicMock()
            re_match.mock_add_spec(spec=Match, spec_set=True)

            event = RegexEvent(
                bot=mock_bot,
                conn=conn,
                match=re_match,
                hook=hook,
                channel="#chan",
            )

            res = regex_chans.sieve_regex(mock_bot, event, hook)

            assert hook.mock_calls == []
            assert plugin.mock_calls == []
            assert conn.mock_calls == []
            assert re_match.mock_calls == []

            assert res is event
            assert caplog.messages == ["[net] Allowing my_func to #chan"]

    @pytest.mark.asyncio
    async def test_no_block_other_hook(
        self, mock_bot_factory, mock_db: MockDB, caplog
    ):
        mock_bot = mock_bot_factory(db=mock_db)
        regex_chans.table.create(mock_db.engine)
        with mock_db.session() as session:
            mock_db.load_data(
                regex_chans.table,
                [
                    {
                        "connection": "net",
                        "channel": "#chan",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan1",
                        "status": "ENABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan2",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net1",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                ],
            )

            regex_chans.load_cache(session)

            conn = MagicMock()
            conn.configure_mock(name="net")
            conn.mock_add_spec(spec=Client, spec_set=True)

            plugin = MagicMock()
            plugin.configure_mock(title="foo")
            plugin.mock_add_spec(spec=Plugin, spec_set=True)

            hook = MagicMock()
            hook.configure_mock(
                type="event", plugin=plugin, function_name="my_func"
            )
            hook.mock_add_spec(spec=EventHook, spec_set=True)

            event = Event(
                bot=mock_bot,
                conn=conn,
                hook=hook,
                channel="#chan",
            )

            res = regex_chans.sieve_regex(mock_bot, event, hook)

            assert hook.mock_calls == []
            assert plugin.mock_calls == []
            assert conn.mock_calls == []

            assert res is event
            assert caplog.messages == []

    @pytest.mark.asyncio
    async def test_allow_other_hook(
        self, mock_bot_factory, mock_db: MockDB, caplog
    ):
        mock_bot = mock_bot_factory(db=mock_db)
        regex_chans.table.create(mock_db.engine)
        with mock_db.session() as session:
            mock_db.load_data(
                regex_chans.table,
                [
                    {
                        "connection": "net",
                        "channel": "#chan",
                        "status": "ENABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan1",
                        "status": "ENABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan2",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                    {
                        "connection": "net1",
                        "channel": "#chan3",
                        "status": "DISABLED",
                    },
                ],
            )

            regex_chans.load_cache(session)

            conn = MagicMock()
            conn.configure_mock(name="net")
            conn.mock_add_spec(spec=Client, spec_set=True)

            plugin = MagicMock()
            plugin.configure_mock(title="foo")
            plugin.mock_add_spec(spec=Plugin, spec_set=True)

            hook = MagicMock()
            hook.configure_mock(
                type="event", plugin=plugin, function_name="my_func"
            )
            hook.mock_add_spec(spec=EventHook, spec_set=True)

            event = Event(
                bot=mock_bot,
                conn=conn,
                hook=hook,
                channel="#chan",
            )

            res = regex_chans.sieve_regex(mock_bot, event, hook)

            assert hook.mock_calls == []
            assert plugin.mock_calls == []
            assert conn.mock_calls == []

            assert res is event
            assert caplog.messages == []


class SetStatusBase:
    def get_command_hook(self):
        raise NotImplementedError

    def get_expected_results(self):
        raise NotImplementedError

    def get_cmd_arg(self) -> str:
        raise NotImplementedError

    def get_expected_db_data(self):
        raise NotImplementedError

    def get_initial_db_data(self):
        return []

    @pytest.mark.asyncio
    async def test_set(self, mock_db: MockDB, mock_bot_factory):
        mock_bot = mock_bot_factory(db=mock_db)
        regex_chans.table.create(mock_db.engine)
        mock_db.load_data(regex_chans.table, self.get_initial_db_data())

        conn = MagicMock()
        conn.configure_mock(name="net", config={})
        conn.mock_add_spec(spec=Client, spec_set=True)

        plugin = MagicMock()
        plugin.configure_mock(title="foo")
        plugin.mock_add_spec(spec=Plugin, spec_set=True)

        hook = MagicMock()
        hook.configure_mock(
            type="event", plugin=plugin, function_name="my_func", doc="foo"
        )
        hook.mock_add_spec(spec=CommandHook, spec_set=True)

        event = CommandEvent(
            bot=mock_bot,
            conn=conn,
            hook=hook,
            channel="#chan",
            text=self.get_cmd_arg(),
            triggered_command="enableregex",
            cmd_prefix=".",
            nick="testnick",
        )

        with mock_db.session() as session:
            event.db = session
            results = wrap_hook_response(self.get_command_hook(), event)

        assert results == self.get_expected_results()

        assert conn.mock_calls == []
        assert plugin.mock_calls == []
        assert hook.mock_calls == []

        assert (
            mock_db.get_data(regex_chans.table) == self.get_expected_db_data()
        )


class TestEnable(SetStatusBase):
    def get_command_hook(self):
        return regex_chans.enableregex

    def get_expected_results(self):
        return [
            (
                "message",
                (
                    "#chan",
                    "Enabling regex matching (youtube, etc) (issued by testnick)",
                ),
            ),
            (
                "notice",
                (
                    "testnick",
                    "Enabling regex matching (youtube, etc) in channel #chan",
                ),
            ),
        ]

    def get_cmd_arg(self) -> str:
        return ""

    def get_expected_db_data(self):
        return [
            ("net", "#chan", "ENABLED"),
        ]


class TestDisable(SetStatusBase):
    def get_command_hook(self):
        return regex_chans.disableregex

    def get_expected_results(self):
        return [
            (
                "message",
                (
                    "#chan",
                    "Disabling regex matching (youtube, etc) (issued by testnick)",
                ),
            ),
            (
                "notice",
                (
                    "testnick",
                    "Disabling regex matching (youtube, etc) in channel #chan",
                ),
            ),
        ]

    def get_cmd_arg(self) -> str:
        return ""

    def get_expected_db_data(self):
        return [
            ("net", "#chan", "DISABLED"),
        ]


class TestEnableWithArg(TestEnable):
    def get_cmd_arg(self) -> str:
        return "#chan2"

    def get_expected_results(self):
        return [
            (
                "message",
                (
                    "#chan2",
                    "Enabling regex matching (youtube, etc) (issued by testnick)",
                ),
            ),
            (
                "notice",
                (
                    "testnick",
                    "Enabling regex matching (youtube, etc) in channel #chan2",
                ),
            ),
        ]

    def get_expected_db_data(self):
        return [
            ("net", "#chan2", "ENABLED"),
        ]


class TestDisableWithArg(TestDisable):
    def get_cmd_arg(self) -> str:
        return "#chan2"

    def get_expected_db_data(self):
        return [
            ("net", "#chan2", "DISABLED"),
        ]

    def get_expected_results(self):
        return [
            (
                "message",
                (
                    "#chan2",
                    "Disabling regex matching (youtube, etc) (issued by testnick)",
                ),
            ),
            (
                "notice",
                (
                    "testnick",
                    "Disabling regex matching (youtube, etc) in channel #chan2",
                ),
            ),
        ]


class TestResetRegex(SetStatusBase):
    def get_cmd_arg(self) -> str:
        return ""

    def get_command_hook(self):
        return regex_chans.resetregex

    def get_expected_results(self):
        return [
            (
                "message",
                (
                    "#chan",
                    "Resetting regex matching setting (youtube, etc) (issued by testnick)",
                ),
            ),
            (
                "notice",
                (
                    "testnick",
                    "Resetting regex matching setting (youtube, etc) in channel #chan",
                ),
            ),
        ]

    def get_expected_db_data(self):
        return []

    def get_initial_db_data(self):
        return [{"connection": "net", "channel": "#chan", "status": "DISABLED"}]


def test_bad_value(mock_db: MockDB, caplog):
    regex_chans.table.create(mock_db.engine)
    mock_db.load_data(
        regex_chans.table,
        [{"connection": "net", "channel": "#chan", "status": "UNKNOWN"}],
    )

    regex_chans.load_cache(mock_db.session())

    assert not regex_chans.status_cache

    assert caplog.messages == [
        "[regex_chans] Unknown status: ('net', '#chan', 'UNKNOWN'), falling back "
        "to default",
    ]
