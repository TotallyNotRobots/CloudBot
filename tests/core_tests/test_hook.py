import re

import pytest


def test_hook_decorate():
    from cloudbot import hook

    from cloudbot.event import EventType

    @hook.event(EventType.message)
    @hook.event([EventType.notice, EventType.action])
    @hook.command('test')
    @hook.irc_raw('*')
    @hook.irc_raw(['PRIVMSG'])
    @hook.irc_out
    @hook.on_stop()
    @hook.regex(['test', re.compile('test')])
    def f():
        pass

    assert f._cloudbot_hook['event'].types == {
        EventType.message, EventType.notice, EventType.action
    }
    assert f._cloudbot_hook['command'].aliases == {'test'}
    assert f._cloudbot_hook['irc_raw'].triggers == {'*', 'PRIVMSG'}
    assert 'irc_out' in f._cloudbot_hook
    assert 'on_stop' in f._cloudbot_hook
    assert 'regex' in f._cloudbot_hook
    assert len(f._cloudbot_hook['regex'].regexes) == 2

    with pytest.raises(ValueError, match="Invalid command name test 123"):
        hook.command('test 123')(f)

    with pytest.raises(TypeError):
        hook.periodic(f)

    with pytest.raises(TypeError):
        hook.regex(f)

    with pytest.raises(TypeError):
        hook.event(f)

    with pytest.raises(TypeError):
        hook.irc_raw(f)

    @hook.sieve
    def sieve_func(bot, event, _hook):
        pass

    assert 'sieve' in sieve_func._cloudbot_hook
