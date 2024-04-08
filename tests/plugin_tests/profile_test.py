from unittest.mock import MagicMock

from cloudbot.event import CommandEvent
from plugins import profile
from tests.util import wrap_hook_response


def test_profile_add(mock_db, mock_bot):
    profile.table.create(mock_db.engine)
    profile.load_cache(mock_db.session())
    conn = MagicMock()
    event = CommandEvent(
        bot=mock_bot,
        conn=conn,
        hook=MagicMock(),
        nick="nick",
        channel="#chan",
        text="foo bar",
        triggered_command="profileadd",
        cmd_prefix=".",
    )
    event.db = mock_db.session()
    res = wrap_hook_response(profile.profileadd, event)
    assert res == [
        ("return", "Created new profile category foo"),
    ]
    assert mock_db.get_data(profile.table) == [("#chan", "nick", "foo", "bar")]
    assert conn.mock_calls == []


def test_profile_update(mock_db, mock_bot):
    profile.table.create(mock_db.engine)
    mock_db.add_row(
        profile.table, chan="#chan", nick="nick", category="foo", text="text"
    )
    profile.load_cache(mock_db.session())
    conn = MagicMock()
    event = CommandEvent(
        bot=mock_bot,
        conn=conn,
        hook=MagicMock(),
        nick="nick",
        channel="#chan",
        text="foo bar",
        triggered_command="profileadd",
        cmd_prefix=".",
    )

    event.db = mock_db.session()
    res = wrap_hook_response(profile.profileadd, event)
    assert res == [
        ("return", "Updated profile category foo"),
    ]
    assert mock_db.get_data(profile.table) == [("#chan", "nick", "foo", "bar")]
    assert conn.mock_calls == []


def test_profile_category_delete(mock_db, mock_bot):
    profile.table.create(mock_db.engine)
    mock_db.add_row(
        profile.table, chan="#chan", nick="nick", category="foo", text="text"
    )
    profile.load_cache(mock_db.session())
    conn = MagicMock()
    event = CommandEvent(
        bot=mock_bot,
        conn=conn,
        hook=MagicMock(),
        nick="nick",
        channel="#chan",
        text="foo",
        triggered_command="profiledel",
        cmd_prefix=".",
    )

    event.db = mock_db.session()
    res = wrap_hook_response(profile.profiledel, event)
    assert res == [("return", "Deleted profile category foo")]
    assert mock_db.get_data(profile.table) == []
    assert conn.mock_calls == []


def test_profile_clear(mock_db, mock_bot):
    profile.table.create(mock_db.engine)
    mock_db.add_row(
        profile.table, chan="#chan", nick="nick", category="foo", text="text"
    )
    mock_db.add_row(
        profile.table, chan="#chan", nick="nick", category="bar", text="thing"
    )
    profile.load_cache(mock_db.session())
    profile.confirm_keys["#chan"]["nick"] = "foo"
    conn = MagicMock()
    event = CommandEvent(
        bot=mock_bot,
        conn=conn,
        hook=MagicMock(),
        nick="nick",
        channel="#chan",
        text="foo",
        triggered_command="profileclear",
        cmd_prefix=".",
    )

    event.db = mock_db.session()
    res = wrap_hook_response(profile.profileclear, event)
    assert res == [
        ("return", "Profile data cleared for nick."),
    ]
    assert mock_db.get_data(profile.table) == []
    assert conn.mock_calls == []
