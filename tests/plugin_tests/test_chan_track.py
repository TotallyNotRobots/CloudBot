import asyncio
from unittest.mock import MagicMock

from irclib.parser import Message, Prefix

from cloudbot.util.func_utils import call_with_args


class MockConn:
    def __init__(self, bot=None):
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
        self.bot = bot

    def get_statuses(self, chars):
        return [
            self.memory['server_info']['statuses'][c]
            for c in chars
        ]


def test_replace_user_data():
    from plugins.core.chan_track import UsersDict, replace_user_data, Channel
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
    from plugins.core.chan_track import (
        get_users, get_chans, replace_user_data,
        on_nick, on_join, on_mode, on_part, on_kick, on_quit,
    )

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

    user = users.getuser('exampleuserfoo')

    assert chan.get_member(user).status == conn.get_statuses('-')

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


NAMES_MOCK_TRAFFIC = [
    ':BotFoo!myname@myhost JOIN #foo',
    ':server.name 353 BotFoo = #foo :BotFoo',
    ':server.name 353 BotFoo = #foo :OtherUser PersonC',
    ':QuickUser!user@host JOIN #foo',
    ':OtherQuickUser!user@host JOIN #foo',
    ':server.name 353 BotFoo = #foo :FooBar123',
    ':server.name 366 BotFoo #foo :End of /NAMES list',
    ':QuickUser!user@host PART #foo',
    ':BotFoo!myname@myhost KICK #foo OtherQuickUser',
]


def test_names_handling():
    from plugins.core.server_info import handle_prefixes, handle_chan_modes
    from plugins.core.chan_track import on_join, on_part, on_kick, on_quit, on_names

    handlers = {
        'JOIN': on_join,
        'PART': on_part,
        'QUIT': on_quit,
        'KICK': on_kick,
        '353': on_names,
        '366': on_names,
    }

    chan_pos = {
        'JOIN': 0,
        'PART': 0,
        'KICK': 0,
        '353': 2,
        '366': 1,
    }

    bot = MagicMock()
    bot.loop = asyncio.get_event_loop()

    conn = MockConn(bot)
    serv_info = conn.memory['server_info']
    handle_prefixes('(YohvV)!@%+-', serv_info)
    handle_chan_modes('IXZbegw,k,FHJLWdfjlx,ABCDKMNOPQRSTcimnprstuz', serv_info)

    for line in NAMES_MOCK_TRAFFIC:
        line = Message.parse(line)
        data = {
            'nick': line.prefix.nick,
            'user': line.prefix.ident,
            'host': line.prefix.host,
            'conn': conn,
            'irc_paramlist': line.parameters,
            'irc_command': line.command,
            'chan': None,
            'target': None,
        }

        if line.command in chan_pos:
            data['chan'] = line.parameters[chan_pos[line.command]]

        if line.command == 'KICK':
            data['target'] = line.parameters[1]

        call_with_args(handlers[line.command], data)
