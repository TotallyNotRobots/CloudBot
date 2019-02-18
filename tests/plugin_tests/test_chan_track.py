import mock
from irclib.parser import Prefix

from plugins.chan_track import Channel
from plugins.core.server_info import DEFAULT_STATUS

statuses = {
    s.prefix: s for s in DEFAULT_STATUS
}
statuses.update({
    s.mode: s for s in DEFAULT_STATUS
})


class MockConn:
    name = 'foo'
    memory = {
        'server_info': {
            'statuses': statuses
        },
        'server_caps': {
            'userhost-in-names': True,
            'multi-prefix': True,
        }
    }


def test_replace_user_data():
    with mock.patch('plugins.chan_track.get_users') as patch:
        from plugins.chan_track import UsersDict
        conn = MockConn()
        users = UsersDict(conn)
        patch.return_value = users

        from plugins.chan_track import replace_user_data
        chan = Channel('#test', conn)
        chan.data['new_users'] = [
            '@+foo!bar@baz',
            '@ExampleUser!bar@baz',
        ]
        replace_user_data(conn, chan)

        assert chan.users['foo'].user.mask == Prefix('foo', 'bar', 'baz')
        assert chan.users['exampleuser'].user.mask == Prefix('ExampleUser', 'bar', 'baz')

        assert chan.users['foo'].status == [statuses['@'], statuses['+']]
