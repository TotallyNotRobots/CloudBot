import time
from unittest.mock import MagicMock

from plugins.core import check_conn


def test_on_act(freeze_time):
    conn = MagicMock(memory={})
    assert check_conn.on_act(conn) is None

    assert conn.memory == {"last_activity": 1566497676.0}

    freeze_time.tick()

    assert conn.memory == {"last_activity": 1566497676.0}

    assert check_conn.on_act(conn) is None

    assert conn.memory == {"last_activity": 1566497677.0}


def test_pong(freeze_time):
    conn = MagicMock(memory={})
    params = ["LAGCHECK" + str(time.time() - 2)]
    assert check_conn.on_pong(conn, params) is None
    assert conn.memory == {
        "lag": 2.0,
        "lag_sent": 0,
        "last_ping_rpl": 1566497676.0,
        "ping_recv": 1566497676.0,
    }
