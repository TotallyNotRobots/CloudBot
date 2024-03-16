from plugins.core import regex_chans
from tests.util.mock_conn import MockConn
from tests.util.mock_db import MockDB


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


def test_listregex(mock_db: MockDB):
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

        conn = MockConn(name="net")
        assert (
            regex_chans.listregex(conn)
            == "#chan: DISABLED, #chan1: ENABLED, #chan2: DISABLED, #chan3: DISABLED"
        )
