from textwrap import dedent

import pytest
from mock import patch, MagicMock, call
from responses import RequestsMock


def test_forget():
    mock_session = MagicMock()
    mock_notice = MagicMock()
    with patch('plugins.factoids.remove_fact') as func:
        from plugins.factoids import forget
        forget('foo bar', '#example', mock_session, mock_notice)

        func.assert_called_with('#example', ['foo', 'bar'], mock_session, mock_notice)


@pytest.fixture
def patch_paste():
    with patch('cloudbot.util.web.paste') as mock:
        yield mock


def test_remove_fact_no_paste():
    from plugins.factoids import factoid_cache
    factoid_cache.clear()
    with RequestsMock() as reqs:
        reqs.add(reqs.POST, 'https://hastebin.com/documents', status=404)
        mock_session = MagicMock()
        mock_notice = MagicMock()

        from plugins.factoids import remove_fact
        remove_fact('#example', ['foo'], mock_session, mock_notice)
        mock_notice.assert_called_once_with("Unknown factoids: 'foo'")

        mock_session.execute.assert_not_called()

        mock_notice.reset_mock()

        factoid_cache['#example']['foo'] = 'bar'

        remove_fact('#example', ['foo', 'bar'], mock_session, mock_notice)
        mock_notice.assert_has_calls([
            call("Unknown factoids: 'bar'"),
            call('Unable to paste removed data, not removing facts'),
        ])

        mock_session.execute.assert_not_called()


def test_remove_fact(patch_paste):
    from plugins.factoids import factoid_cache
    factoid_cache.clear()
    mock_session = MagicMock()
    mock_notice = MagicMock()

    from plugins.factoids import remove_fact
    remove_fact('#example', ['foo'], mock_session, mock_notice)
    mock_notice.assert_called_with("Unknown factoids: 'foo'")

    mock_session.execute.assert_not_called()

    factoid_cache['#example']['foo'] = 'bar'

    patch_paste.return_value = "PASTEURL"
    remove_fact('#example', ['foo'], mock_session, mock_notice)
    mock_notice.assert_called_with('Removed Data: PASTEURL')
    patch_paste.assert_called_with(
        b'| Command | Output |\n| ------- | ------ |\n| ?foo    | bar    |',
        'md', 'hastebin', raise_on_no_paste=True
    )

    query = mock_session.execute.mock_calls[0][1][0]

    compiled = query.compile()

    assert str(compiled) == dedent("""
    DELETE FROM factoids WHERE factoids.chan = :chan_1 AND factoids.word IN (:word_1)
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
