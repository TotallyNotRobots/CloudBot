import importlib

import pytest
from mock import MagicMock


@pytest.mark.parametrize('prefix,items,result', [
    [
        'Duck friend scores in #TestChannel: ',
        {
            'testuser': 5,
            'testuser1': 1,
        },
        'Duck friend scores in #TestChannel: '
        '\x02t\u200bestuser\x02: 5 • \x02t\u200bestuser1\x02: 1'
    ],
])
def test_top_list(prefix, items, result):
    from plugins.duckhunt import top_list
    assert top_list(prefix, items.items()) == result


def test_display_scores(mock_db):
    from cloudbot.util import database
    importlib.reload(database)
    database.metadata.bind = mock_db.engine
    from plugins import duckhunt

    importlib.reload(duckhunt)

    database.metadata.create_all(checkfirst=True)

    session = mock_db.session()

    class Conn:
        name = 'TestConn'

    conn = Conn()

    chan = '#TestChannel'
    chan1 = '#TestChannel1'

    duckhunt.update_score('TestUser', chan, session, conn, 5, 4)
    duckhunt.update_score('TestUser1', chan, session, conn, 1, 7)
    duckhunt.update_score('OtherUser', chan1, session, conn, 9, 2)

    expected_testchan_friend_scores = {'testuser': 4, 'testuser1': 7}

    actual_testchan_friend_scores = duckhunt.get_channel_scores(
        session, duckhunt.SCORE_TYPES['friend'],
        conn, chan
    )

    assert actual_testchan_friend_scores == expected_testchan_friend_scores

    chan_friends = (
        'Duck friend scores in #TestChannel: '
        '\x02t\u200bestuser1\x02: 7 • \x02t\u200bestuser\x02: 4'
    )

    chan_kills = (
        'Duck killer scores in #TestChannel: '
        '\x02t\u200bestuser\x02: 5 • \x02t\u200bestuser1\x02: 1'
    )

    global_friends = (
        'Duck friend scores across the network: '
        '\x02t\u200bestuser1\x02: 7'
        ' • \x02t\u200bestuser\x02: 4'
        ' • \x02o\u200btheruser\x02: 2'
    )

    global_kills = (
        'Duck killer scores across the network: '
        '\x02o\u200btheruser\x02: 9'
        ' • \x02t\u200bestuser\x02: 5'
        ' • \x02t\u200bestuser1\x02: 1'
    )

    average_friends = (
        'Duck friend scores across the network: '
        '\x02t\u200bestuser1\x02: 7'
        ' • \x02t\u200bestuser\x02: 4'
        ' • \x02o\u200btheruser\x02: 2'
    )

    average_kills = (
        'Duck killer scores across the network: '
        '\x02o\u200btheruser\x02: 9'
        ' • \x02t\u200bestuser\x02: 5'
        ' • \x02t\u200bestuser1\x02: 1'
    )

    event = MagicMock()

    assert duckhunt.friends('', event, chan, conn, session) == chan_friends

    assert duckhunt.killers('', event, chan, conn, session) == chan_kills

    assert duckhunt.friends('global', event, chan, conn, session) == global_friends

    assert duckhunt.killers('global', event, chan, conn, session) == global_kills

    assert duckhunt.friends('average', event, chan, conn, session) == average_friends

    assert duckhunt.killers('average', event, chan, conn, session) == average_kills

    event.reset_mock()

    assert duckhunt.killers('#channel', event, chan, conn, session) is None

    event.notice_doc.assert_called_once()
