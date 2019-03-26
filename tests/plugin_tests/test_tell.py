import importlib

from irclib.parser import Prefix
from mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

Session = scoped_session(sessionmaker())


def test_tellcmd():
    from cloudbot.util import database
    from plugins import tell
    database = importlib.reload(database)
    tell = importlib.reload(tell)
    metadata = database.metadata

    assert 'tells' in metadata.tables
    assert 'tell_ignores' in metadata.tables
    assert 'tell_user_ignores' in metadata.tables

    db_engine = create_engine('sqlite:///:memory:')
    Session.configure(bind=db_engine)
    metadata.create_all(db_engine)
    session = Session()
    tell.load_cache(session)
    tell.load_disabled(session)
    tell.load_ignores(session)

    mock_event = MagicMock()
    mock_event.is_nick_valid.return_value = True
    mock_conn = MagicMock()
    mock_conn.nick = "BotNick"
    mock_conn.name = "MockConn"
    sender = Prefix("TestUser", "user", "example.com")
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

    tell.tell_cmd(
        "OtherUser some message",
        sender.nick,
        session,
        mock_conn,
        sender.mask,
        mock_event,
    )

    mock_event.notice.assert_called_with(
        "Your message has been saved, and OtherUser will be notified once they are active."
    )

    mock_event.reset_mock()

    for _ in range(9):
        tell.tell_cmd(
            "OtherUser some message",
            sender.nick,
            session,
            mock_conn,
            sender.mask,
            mock_event,
        )

        mock_event.notice.assert_called_with(
            "Your message has been saved, and OtherUser will be notified once they are active."
        )

        mock_event.reset_mock()

    tell.tell_cmd(
        "OtherUser some message",
        sender.nick,
        session,
        mock_conn,
        sender.mask,
        mock_event,
    )

    mock_event.notice.assert_called_with(
        "Sorry, OtherUser has too many messages queued already."
    )

    mock_event.reset_mock()

    mock_event.is_nick_valid.return_value = False
    tell.tell_cmd(
        "OtherUser some message",
        sender.nick,
        session,
        mock_conn,
        sender.mask,
        mock_event,
    )

    mock_event.notice.assert_called_with(
        "Invalid nick 'OtherUser'."
    )

    mock_event.reset_mock()

    mock_event.is_nick_valid.return_value = True
    tell.tell_cmd(
        sender.nick + " some message",
        sender.nick,
        session,
        mock_conn,
        sender.mask,
        mock_event,
    )

    mock_event.notice.assert_called_with(
        "Have you looked in a mirror lately?"
    )

    mock_event.reset_mock()

    with patch('plugins.tell.can_send_to_user') as mocked:
        mocked.return_value = False
        tell.tell_cmd(
            "OtherUser some message",
            sender.nick,
            session,
            mock_conn,
            sender.mask,
            mock_event,
        )

        mock_event.notice.assert_called_with(
            "You may not send a tell to that user."
        )

        mock_event.reset_mock()
