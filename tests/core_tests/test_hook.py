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
    @hook.regex('test1')
    @hook.regex(re.compile('test2'))
    def f():
        pass  # pragma: no cover

    assert f._cloudbot_hook['event'].types == {
        EventType.message, EventType.notice, EventType.action
    }
    assert f._cloudbot_hook['command'].aliases == {'test'}
    assert f._cloudbot_hook['irc_raw'].triggers == {'*', 'PRIVMSG'}
    assert 'irc_out' in f._cloudbot_hook
    assert 'on_stop' in f._cloudbot_hook
    assert 'regex' in f._cloudbot_hook
    assert len(f._cloudbot_hook['regex'].regexes) == 4

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
        pass  # pragma: no cover

    assert 'sieve' in sieve_func._cloudbot_hook


def test_command_hook_doc():
    from cloudbot import hook

    @hook.command
    def test(bot):
        """<arg> - foo
        bar
        baz

        :type bot: object"""

    cmd_hook = test._cloudbot_hook['command']
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command
    def test1(bot):
        """<arg> - foo bar baz

        :type bot: object"""

    cmd_hook = test1._cloudbot_hook['command']
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command
    def test2(bot):
        """<arg> - foo bar baz"""

    cmd_hook = test2._cloudbot_hook['command']
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command
    def test3(bot):
        """
        <arg> - foo bar baz
        """

    cmd_hook = test3._cloudbot_hook['command']
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command
    def test4(bot):
        """<arg> - foo bar baz
        """

    cmd_hook = test4._cloudbot_hook['command']
    assert cmd_hook.doc == "<arg> - foo bar baz"
