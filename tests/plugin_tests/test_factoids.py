from textwrap import dedent

from mock import patch, MagicMock, call


def test_forget():
    mock_session = MagicMock()
    mock_notice = MagicMock()
    with patch('plugins.factoids.remove_fact') as func:
        from plugins.factoids import forget
        forget('foo bar', '#example', mock_session, mock_notice)

        func.assert_has_calls([
            call('#example', 'foo', mock_session, mock_notice),
            call('#example', 'bar', mock_session, mock_notice),
        ])


def test_remove_fact():
    mock_session = MagicMock()
    mock_notice = MagicMock()

    from plugins.factoids import remove_fact
    remove_fact('#example', 'foo', mock_session, mock_notice)
    mock_notice.assert_called_with("Unknown fact 'foo'")

    mock_session.execute.assert_not_called()

    from plugins.factoids import factoid_cache
    factoid_cache['#example']['foo'] = 'bar'

    remove_fact('#example', 'foo', mock_session, mock_notice)
    mock_notice.assert_called_with("'foo' has been forgotten, previous value was 'bar'")

    query = mock_session.execute.mock_calls[0][1][0]

    compiled = query.compile()

    assert str(compiled) == dedent("""
    DELETE FROM factoids WHERE factoids.chan = :chan_1 AND factoids.word = :word_1
    """).strip()

    assert compiled.params == {'chan_1': '#example', 'word_1': 'foo'}


def test_clear_facts():
    mock_session = MagicMock()

    from plugins.factoids import forget_all
    assert forget_all('#example', mock_session) == "Facts cleared."

    query = mock_session.execute.mock_calls[0][1][0]

    compiled = query.compile()

    assert str(compiled) == dedent("""
    DELETE FROM factoids WHERE factoids.chan = :chan_1
    """).strip()

    assert compiled.params == {'chan_1': '#example'}
