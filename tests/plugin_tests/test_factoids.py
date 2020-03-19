import importlib
import itertools
import string
from textwrap import dedent
from unittest.mock import MagicMock, call, patch


def test_forget():
    from cloudbot.util import database
    from plugins import factoids
    importlib.reload(database)
    importlib.reload(factoids)

    mock_session = MagicMock()
    mock_notice = MagicMock()
    with patch('plugins.factoids.remove_fact') as func:
        from plugins.factoids import forget
        forget('foo bar', '#example', mock_session, mock_notice)

        func.assert_called_with('#example', ['foo', 'bar'], mock_session, mock_notice)


def test_remove_fact_no_paste(mock_requests):
    from cloudbot.util import database
    from plugins import factoids
    importlib.reload(database)
    importlib.reload(factoids)

    factoids.factoid_cache.clear()
    mock_requests.add(mock_requests.POST, 'https://hastebin.com/documents', status=404)
    mock_session = MagicMock()
    mock_notice = MagicMock()

    factoids.remove_fact('#example', ['foo'], mock_session, mock_notice)
    mock_notice.assert_called_once_with("Unknown factoids: 'foo'")

    mock_session.execute.assert_not_called()

    mock_notice.reset_mock()

    factoids.factoid_cache['#example']['foo'] = 'bar'

    factoids.remove_fact('#example', ['foo', 'bar'], mock_session, mock_notice)
    mock_notice.assert_has_calls([
        call("Unknown factoids: 'bar'"),
        call('Unable to paste removed data, not removing facts'),
    ])

    mock_session.execute.assert_not_called()


def test_remove_fact(patch_paste):
    from cloudbot.util import database
    from plugins import factoids
    importlib.reload(database)
    importlib.reload(factoids)

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
    from cloudbot.util import database
    from plugins import factoids
    importlib.reload(database)
    importlib.reload(factoids)

    mock_session = MagicMock()

    from plugins.factoids import forget_all
    assert forget_all('#example', mock_session) == "Facts cleared."

    query = mock_session.execute.mock_calls[0][1][0]

    compiled = query.compile()

    assert str(compiled) == dedent("""
    DELETE FROM factoids WHERE factoids.chan = :chan_1
    """).strip()

    assert compiled.params == {'chan_1': '#example'}


def test_list_facts(mock_db):
    from plugins import factoids

    factoids.table.create(mock_db.engine, checkfirst=True)

    names = [
        ''.join(c) for c in itertools.product(string.ascii_lowercase, repeat=2)
    ]

    for name in names:
        factoids.add_factoid(
            mock_db.session(),
            name.lower(),
            '#chan',
            name,
            'nick',
        )

    notice = MagicMock()
    factoids.listfactoids(notice, '#chan')

    text = ', '.join(call[1][0] for call in notice.mock_calls)

    assert text == ', '.join(
        '?' + name for name in sorted(names + ['commands'])
    )
