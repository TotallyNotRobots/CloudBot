import importlib
from unittest.mock import MagicMock, patch

from irclib.parser import Prefix


def test_tellcmd(mock_db):
    from cloudbot.util import database
    from plugins import tell
    database = importlib.reload(database)
    importlib.reload(tell)
    metadata = database.metadata

    assert 'tells' in metadata.tables
    assert 'tell_ignores' in metadata.tables
    assert 'tell_user_ignores' in metadata.tables

    db_engine = mock_db.engine
    metadata.create_all(db_engine)
    session = mock_db.session()

    tell.load_cache(session)
    tell.load_disabled(session)
    tell.load_ignores(session)

    mock_event = MagicMock()
    mock_event.is_nick_valid.return_value = True
    mock_conn = MagicMock()
    mock_conn.nick = "BotNick"
    mock_conn.name = "MockConn"
    sender = Prefix("TestUser", "user", "example.com")

    def _test(text, output):
        tell.tell_cmd(
            text,
            sender.nick,
            session,
            mock_conn,
            sender.mask,
            mock_event,
        )

        mock_event.notice.assert_called_with(output)

        mock_event.reset_mock()

    tell.tell_cmd(
        "OtherUser",
        sender.nick,
        session,
        mock_conn,
        sender.mask,
        mock_event,
    )

    mock_event.notice_doc.assert_called_once_with()

    mock_event.reset_mock()

    _test(
        "OtherUser some message",
        "Your message has been saved, and OtherUser will be notified once they are active."
    )

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 1

    for i in range(9):
        _test(
            "OtherUser some message",
            "Your message has been saved, and OtherUser will be notified once they are active."
        )

        assert tell.count_unread(session, mock_conn.name, "OtherUser") == 2 + i

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10

    _test(
        "OtherUser some message",
        "Sorry, OtherUser has too many messages queued already."
    )

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10

    mock_event.is_nick_valid.return_value = False

    _test(
        "OtherUser some message",
        "Invalid nick 'OtherUser'."
    )

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10

    mock_event.is_nick_valid.return_value = True
    _test(
        sender.nick + " some message",
        "Have you looked in a mirror lately?"
    )

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10

    with patch('plugins.tell.can_send_to_user') as mocked:
        mocked.return_value = False
        _test(
            "OtherUser some message",
            "You may not send a tell to that user."
        )

    assert tell.count_unread(session, mock_conn.name, "OtherUser") == 10
