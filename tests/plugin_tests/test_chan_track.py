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
        self.nick = 'BotFoo'

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
    assert not chan.users['exampleuser2'].status


def test_channel_members():
    from plugins.core.server_info import handle_prefixes, handle_chan_modes
    from plugins.chan_track import get_users, get_chans, replace_user_data, \
        on_nick, on_join, on_mode, on_part, on_kick, on_quit

    conn = MockConn()
    serv_info = conn.memory['server_info']
    handle_prefixes('(YohvV)!@%+-', serv_info)
    handle_chan_modes('IXZbegw,k,FHJLWdfjlx,ABCDKMNOPQRSTcimnprstuz', serv_info)
    users = get_users(conn)
    chans = get_chans(conn)

    chan = chans.getchan('#foo')
    assert chan.name == '#foo'

    chan.data['new_users'] = [
        '@+foo!bar@baz',
        '@ExampleUser!bar@baz',
        '-ExampleUser2!bar@baz',
        '!@%+-foo1!bar@baz',
    ]
    replace_user_data(conn, chan)

    assert users['exampleuser'].host == 'baz'

    test_user = users['exampleuser2']
    on_nick('exampleuser2', ['ExampleUserFoo'], conn)

    assert test_user.nick == 'ExampleUserFoo'
    assert 'exampleuserfoo' in chan.users

    assert chan.get_member(users.getuser('exampleuserfoo')).status == conn.get_statuses('-')

    on_join('nick1', 'user', 'host', conn, ['#bar'])

    assert users['Nick1'].host == 'host'

    assert chans['#Bar'].users['Nick1'].status == conn.get_statuses('')

    on_mode(chan.name, [chan.name, '+sop', test_user.nick], conn)

    assert chan.get_member(test_user).status == conn.get_statuses('@-')

    on_part(chan.name, test_user.nick, conn)

    assert test_user.nick not in chan.users

    assert 'foo' in chan.users
    on_kick(chan.name, 'foo', conn)
    assert 'foo' not in chan.users

    assert 'foo1' in chan.users
    on_quit('foo1', conn)
    assert 'foo1' not in chan.users
