from unittest.mock import MagicMock, patch

from plugins.core import optout
from plugins.core.optout import get_conn_optouts, optout_cache


def test_conn_case():
    conn_list = optout_cache["TestConnection"]

    assert get_conn_optouts("TestConnection") is conn_list
    assert get_conn_optouts("testconnection") is conn_list
    assert get_conn_optouts("testconnection1") is not conn_list

    conn_list = optout_cache["testconnection"]

    assert get_conn_optouts("TestConnection") is conn_list
    assert get_conn_optouts("testconnection") is conn_list
    assert get_conn_optouts("testconnection1") is not conn_list


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
