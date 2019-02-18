from irclib.parser import Prefix


class MockConn:
    def __init__(self):
        self.name = 'foo'
        self.memory = {
            'server_info': {
                'statuses': {},
            },
            'server_caps': {
                'userhost-in-names': True,
                'multi-prefix': True,
            }
        }

    def get_statuses(self, chars):
        return [
            self.memory['server_info']['statuses'][c]
            for c in chars
        ]


def test_replace_user_data():
    from plugins.chan_track import UsersDict, replace_user_data, Channel
    from plugins.core.server_info import handle_prefixes
    conn = MockConn()
    serv_info = conn.memory['server_info']
    handle_prefixes('(YohvV)!@%+-', serv_info)
    users = UsersDict(conn)
    conn.memory['users'] = users

    chan = Channel('#test', conn)
    chan.data['new_users'] = [
        '@+foo!bar@baz',
        '@ExampleUser!bar@baz',
        'ExampleUser2!bar@baz',
        '!@%+-foo1!bar@baz',
    ]
    replace_user_data(conn, chan)

    assert chan.users['foo'].user.mask == Prefix('foo', 'bar', 'baz')
    assert chan.users['foo1'].user.mask == Prefix('foo1', 'bar', 'baz')
    assert chan.users['exampleuser'].user.mask == Prefix(
        'ExampleUser', 'bar', 'baz'
    )
    assert chan.users['exampleuser2'].user.mask == Prefix(
        'ExampleUser2', 'bar', 'baz'
    )

    assert chan.users['foo'].status == conn.get_statuses('@+')
    assert chan.users['exampleuser'].status == conn.get_statuses('@')
    assert chan.users['Foo1'].status == conn.get_statuses('!@%+-')
    assert len(chan.users['exampleuser2'].status) == 0
