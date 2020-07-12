import datetime
from unittest.mock import MagicMock

from cloudbot.event import CommandEvent
from plugins import notes
from tests.util import wrap_hook_response
from tests.util.mock_bot import MockBot


def test_note_add(mock_db, freeze_time):
    notes.table.create(mock_db.engine, checkfirst=True)
    bot = MockBot({}, db=mock_db)
    conn = MagicMock()
    conn.name = "foobot"
    event = CommandEvent(
        cmd_prefix=".",
        triggered_command="note",
        text="add hi",
        hook=MagicMock(required_args=["db"]),
        conn=conn,
        nick="foonick",
        bot=bot,
    )
    event.prepare_threaded()
    res = wrap_hook_response(notes.note, event)
    assert res == [("message", ("foonick", "Note added!"))]
    assert mock_db.get_data(notes.table) == [
        (
            1,
            "foobot",
            "foonick",
            "hi",
            None,
            False,
            datetime.datetime(2019, 8, 22, 19, 14, 36),
        )
    ]
