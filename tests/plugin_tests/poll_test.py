from unittest.mock import MagicMock

from cloudbot.event import CommandEvent
from plugins import poll
from tests.util import wrap_hook_response


def test_poll():
    conn = MagicMock()
    conn.configure_mock(name="fooconn")
    event = CommandEvent(
        channel="#foo",
        text="Should we party?",
        triggered_command="poll",
        cmd_prefix=".",
        hook=MagicMock(),
        nick="foonick",
        conn=conn,
        bot=MagicMock(),
    )
    assert wrap_hook_response(poll.poll, event) == [
        (
            "message",
            (
                "#foo",
                'Created poll \x02"Should we party?"\x02 with the following '
                "options: Yes and No",
            ),
        ),
        (
            "message",
            ("#foo", "Use .vote foonick <option> to vote on this poll!"),
        ),
    ]

    poll_obj = poll.polls["fooconn:#foo:foonick"]  # type: poll.Poll

    assert poll_obj.voted == []
    assert poll_obj.options["yes"].votes == 0
    assert poll_obj.options["no"].votes == 0

    event = CommandEvent(
        channel="#foo",
        text="foonick yes",
        triggered_command="vote",
        cmd_prefix=".",
        hook=MagicMock(),
        nick="foonick1",
        conn=conn,
        bot=MagicMock(),
    )

    assert wrap_hook_response(poll.vote, event) == [
        ("message", ("foonick1", 'Voted \x02"Yes"\x02 on foonick\'s poll!'))
    ]

    assert poll_obj.voted == ["foonick1"]
    assert poll_obj.options["yes"].votes == 1
    assert poll_obj.options["no"].votes == 0

    event = CommandEvent(
        channel="#foo",
        text="close",
        triggered_command="poll",
        cmd_prefix=".",
        hook=MagicMock(),
        nick="foonick",
        conn=conn,
        bot=MagicMock(),
    )

    assert wrap_hook_response(poll.poll, event) == [
        (
            "message",
            (
                "#foo",
                "(foonick) Your poll has been closed. Final results for "
                '\x02"Should we party?"\x02:',
            ),
        ),
        ("message", ("#foo", "Yes: 1, No: 0")),
    ]
