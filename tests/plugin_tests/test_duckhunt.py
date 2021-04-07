from unittest.mock import MagicMock, call, patch

import pytest

from plugins import duckhunt
from tests.util.mock_conn import MockConn


@pytest.mark.parametrize(
    "prefix,items,result",
    [
        [
            "Duck friend scores in #TestChannel: ",
            {
                "testuser": 5,
                "testuser1": 1,
            },
            "Duck friend scores in #TestChannel: "
            "\x02t\u200bestuser\x02: 5 • \x02t\u200bestuser1\x02: 1",
        ],
    ],
)
def test_top_list(prefix, items, result, mock_db):
    assert duckhunt.top_list(prefix, items.items()) == result


def test_display_scores(mock_db):
    duckhunt.table.create(mock_db.engine)

    session = mock_db.session()

    conn = MockConn()

    chan = "#TestChannel"
    chan1 = "#TestChannel1"

    duckhunt.update_score("TestUser", chan, session, conn, 5, 4)
    duckhunt.update_score("TestUser1", chan, session, conn, 1, 7)
    duckhunt.update_score("OtherUser", chan1, session, conn, 9, 2)

    expected_testchan_friend_scores = {"testuser": 4, "testuser1": 7}

    actual_testchan_friend_scores = duckhunt.get_channel_scores(
        session, duckhunt.SCORE_TYPES["friend"], conn, chan
    )

    assert actual_testchan_friend_scores == expected_testchan_friend_scores

    chan_friends = (
        "Duck friend scores in #TestChannel: "
        "\x02t\u200bestuser1\x02: 7 • \x02t\u200bestuser\x02: 4"
    )

    chan_kills = (
        "Duck killer scores in #TestChannel: "
        "\x02t\u200bestuser\x02: 5 • \x02t\u200bestuser1\x02: 1"
    )

    global_friends = (
        "Duck friend scores across the network: "
        "\x02t\u200bestuser1\x02: 7"
        " • \x02t\u200bestuser\x02: 4"
        " • \x02o\u200btheruser\x02: 2"
    )

    global_kills = (
        "Duck killer scores across the network: "
        "\x02o\u200btheruser\x02: 9"
        " • \x02t\u200bestuser\x02: 5"
        " • \x02t\u200bestuser1\x02: 1"
    )

    average_friends = (
        "Duck friend scores across the network: "
        "\x02t\u200bestuser1\x02: 7"
        " • \x02t\u200bestuser\x02: 4"
        " • \x02o\u200btheruser\x02: 2"
    )

    average_kills = (
        "Duck killer scores across the network: "
        "\x02o\u200btheruser\x02: 9"
        " • \x02t\u200bestuser\x02: 5"
        " • \x02t\u200bestuser1\x02: 1"
    )

    event = MagicMock()

    assert duckhunt.friends("", event, chan, conn, session) == chan_friends

    assert duckhunt.killers("", event, chan, conn, session) == chan_kills

    assert (
        duckhunt.friends("global", event, chan, conn, session) == global_friends
    )

    assert (
        duckhunt.killers("global", event, chan, conn, session) == global_kills
    )

    assert (
        duckhunt.friends("average", event, chan, conn, session)
        == average_friends
    )

    assert (
        duckhunt.killers("average", event, chan, conn, session) == average_kills
    )

    event.reset_mock()

    assert duckhunt.killers("#channel", event, chan, conn, session) is None

    assert event.notice_doc.call_count == 1


def test_ignore_integration(mock_db):
    event = MagicMock()
    event.chan = "#chan"
    event.mask = "nick!user@host"
    event.host = "host"

    ignore_plugin = MagicMock()

    ignore_plugin.code.is_ignored.return_value = True

    plugins = {
        "core.ignore": ignore_plugin,
    }

    def find_plugin(name):
        return plugins.get(name)

    event.bot.plugin_manager.find_plugin = find_plugin

    conn = event.conn
    conn.name = "testconn"

    tbl = duckhunt.get_state_table(conn.name, event.chan)
    tbl.game_on = True
    tbl.duck_status = 0

    duckhunt.increment_msg_counter(event, conn)

    assert not tbl.masks

    ignore_plugin.code.is_ignored.return_value = False

    duckhunt.increment_msg_counter(event, conn)

    assert tbl.masks == [event.host]


def test_no_duck_kick_opt_out(mock_db):
    duckhunt.status_table.create(mock_db.engine)
    with patch.object(duckhunt, "is_opt_out") as mocked:
        mocked.return_value = True
        db = mock_db.session()
        conn = MockConn()
        event = MagicMock()
        chan = "#foo"
        res = duckhunt.no_duck_kick(db, "foo", chan, conn, event.notice_doc)
        assert res is None
        assert mock_db.get_data(duckhunt.status_table) == []
        assert event.mock_calls == []


def test_stop_hunt_opt_out(mock_db):
    duckhunt.status_table.create(mock_db.engine)
    with patch.object(duckhunt, "is_opt_out") as mocked:
        mocked.return_value = True
        db = mock_db.session()
        conn = MockConn()
        chan = "#foo"
        res = duckhunt.stop_hunt(db, chan, conn)
        assert res is None
        assert mock_db.get_data(duckhunt.status_table) == []


def test_start_hunt_opt_out(mock_db):
    duckhunt.status_table.create(mock_db.engine)
    with patch.object(duckhunt, "is_opt_out") as mocked:
        mocked.return_value = True
        db = mock_db.session()
        conn = MockConn()
        event = MagicMock()
        chan = "#foo"
        res = duckhunt.start_hunt(db, chan, event.mesage, conn)
        assert res is None
        assert event.mock_calls == []
        assert mock_db.get_data(duckhunt.status_table) == []


def test_start_hunt(mock_db):
    duckhunt.status_table.create(mock_db.engine)
    db = mock_db.session()
    conn = MockConn()
    event = MagicMock()
    chan = "#foo"
    res = duckhunt.start_hunt(db, chan, event.mesage, conn)
    assert res is None
    assert event.mock_calls == [
        call.mesage(
            "Ducks have been spotted nearby. See how many you can shoot or save. use .bang to shoot or .befriend to save them. NOTE: Ducks now appear as a function of time and channel activity.",
            "#foo",
        )
    ]
    assert mock_db.get_data(duckhunt.status_table) == [
        ("testconn", "#foo", True, False)
    ]


def test_duck_migrate_no_data(mock_db):
    duckhunt.table.create(mock_db.engine)
    conn = MockConn()
    event = MagicMock()
    db = mock_db.session()
    text = "a b"
    message = event.message
    res = duckhunt.duck_merge(text, conn, db, message)
    assert res == "There are no duck scores to migrate from a"
    assert event.mock_calls == []
    assert mock_db.get_data(duckhunt.table) == []


def test_duck_migrate(mock_db):
    duckhunt.table.create(mock_db.engine)
    conn = MockConn()
    conn.name = "foo"
    mock_db.add_row(
        duckhunt.table,
        network=conn.name,
        name="bar",
        shot=12,
        befriend=10,
        chan="#test",
    )

    mock_db.add_row(
        duckhunt.table,
        network=conn.name,
        name="bar",
        shot=9,
        befriend=8,
        chan="#test1",
    )

    mock_db.add_row(
        duckhunt.table,
        network=conn.name,
        name="other",
        shot=3,
        befriend=0,
        chan="#test1",
    )

    event = MagicMock()
    db = mock_db.session()
    text = "bar other"
    message = event.message
    res = duckhunt.duck_merge(text, conn, db, message)

    assert event.mock_calls == [
        call.message(
            "Migrated 21 duck kills and 18 duck friends from bar to other"
        )
    ]
    assert mock_db.get_data(duckhunt.table) == [
        ("foo", "other", 12, 8, "#test1"),
        ("foo", "other", 12, 10, "#test"),
    ]
    assert res is None


def test_duck_stats_user_single_chan(mock_db):
    duckhunt.table.create(mock_db.engine)
    chan = "#foo"
    nick = "foobar"
    conn = MockConn()
    mock_db.add_row(
        duckhunt.table,
        network=conn.name,
        name=nick,
        shot=20,
        befriend=18,
        chan=chan.lower(),
    )
    event = MagicMock()
    db = mock_db.session()
    text = ""
    message = event.message
    res = duckhunt.ducks_user(text, nick, chan, conn, db, message)
    assert res is None
    assert event.mock_calls == [
        call.message(
            "foobar has killed 20 ducks and befriended 18 ducks in #foo."
        )
    ]


def test_duck_stats_no_data(mock_db):
    duckhunt.table.create(mock_db.engine)
    conn = MockConn()
    event = MagicMock()
    chan = "#foo"
    db = mock_db.session()
    res = duckhunt.duck_stats(chan, conn, db, event.message)
    assert (
        res
        == "It looks like there has been no duck activity on this channel or network."
    )
    assert event.mock_calls == []
