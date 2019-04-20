import importlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from plugins.duckhunt import top_list


class MockDB:
    def __init__(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.session = scoped_session(sessionmaker(self.engine))


@pytest.fixture()
def mock_db():
    return MockDB()


@pytest.mark.parametrize('prefix,items,result', [
    (
            'Duck friend scores in #TestChannel: ',
            {
                'testuser': 5,
                'testuser1': 1,
            },
            'Duck friend scores in #TestChannel: \x02t\u200bestuser\x02: 5 • \x02t\u200bestuser1\x02: 1'
    ),
])
def test_top_list(prefix, items, result):
    assert top_list(prefix, items.items()) == result


def test_display_scores(mock_db):
    from cloudbot.util.database import metadata
    metadata.bind = mock_db.engine
    from plugins import duckhunt

    importlib.reload(duckhunt)

    metadata.create_all(checkfirst=True)

    session = mock_db.session()

    class Conn:
        name = 'TestConn'

    conn = Conn()

    duckhunt.update_score('TestUser', '#TestChannel', session, conn, 5, 4)
    duckhunt.update_score('TestUser1', '#TestChannel', session, conn, 1, 7)
    duckhunt.update_score('OtherUser', '#TestChannel1', session, conn, 9, 2)

    assert duckhunt.get_channel_scores(
        session, duckhunt.SCORE_TYPES['friend'], conn, '#TestChannel'
    ) == {'testuser': 4, 'testuser1': 7}

    assert repr(duckhunt.friends('', '#TestChannel', conn, session)) == repr(
        'Duck friend scores in #TestChannel: '
        '\x02t\u200bestuser1\x02: 7 • \x02t\u200bestuser\x02: 4'
    )

    assert repr(duckhunt.killers('', '#TestChannel', conn, session)) == repr(
        'Duck killer scores in #TestChannel: '
        '\x02t\u200bestuser\x02: 5 • \x02t\u200bestuser1\x02: 1'
    )

    assert repr(duckhunt.friends('global', '#TestChannel', conn, session)) == repr(
        'Duck friend scores across the network: '
        '\x02t\u200bestuser1\x02: 7'
        ' • \x02t\u200bestuser\x02: 4'
        ' • \x02o\u200btheruser\x02: 2'
    )

    assert repr(duckhunt.killers('global', '#TestChannel', conn, session)) == repr(
        'Duck killer scores across the network: '
        '\x02o\u200btheruser\x02: 9'
        ' • \x02t\u200bestuser\x02: 5'
        ' • \x02t\u200bestuser1\x02: 1'
    )

    assert repr(duckhunt.friends('average', '#TestChannel', conn, session)) == repr(
        'Duck friend scores across the network: '
        '\x02t\u200bestuser1\x02: 7'
        ' • \x02t\u200bestuser\x02: 4'
        ' • \x02o\u200btheruser\x02: 2'
    )

    assert repr(duckhunt.killers('average', '#TestChannel', conn, session)) == repr(
        'Duck killer scores across the network: '
        '\x02o\u200btheruser\x02: 9'
        ' • \x02t\u200bestuser\x02: 5'
        ' • \x02t\u200bestuser1\x02: 1'
    )
