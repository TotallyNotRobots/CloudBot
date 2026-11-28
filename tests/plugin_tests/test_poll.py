from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call

from plugins import poll
from tests.util.mock_conn import MockClient

if TYPE_CHECKING:
    from tests.util.mock_bot import MockBot


def test_poll_close(mock_bot: MockBot) -> None:
    poll.polls.clear()
    text = "close"
    conn = MockClient(bot=mock_bot)
    nick = "foo"
    chan = "#bar"
    event = MagicMock()
    message = event.message
    reply = event.reply
    uid = f"{conn.name}:{chan}:{nick}".lower()
    poll.polls[uid] = poll.Poll("thing?", nick)
    res = poll.poll(text, conn, nick, chan, message, reply)
    assert res is None
    assert event.mock_calls == [
        call.reply(
            'Your poll has been closed. Final results for \x02"thing?"\x02:'
        ),
        call.message("Yes: 0, No: 0"),
    ]
    assert uid not in poll.polls


def test_poll_create(mock_bot: MockBot) -> None:
    poll.polls.clear()
    text = "thing?: yes yes no"
    conn = MockClient(bot=mock_bot)
    nick = "foo"
    chan = "#bar"
    event = MagicMock()
    message = event.message
    reply = event.reply
    uid = f"{conn.name}:{chan}:{nick}".lower()
    res = poll.poll(text, conn, nick, chan, message, reply)
    assert res is None
    assert event.mock_calls == [
        call.message(
            'Created poll \x02"thing?"\x02 with the following options: yes and no'
        ),
        call.message("Use .vote foo <option> to vote on this poll!"),
    ]
    assert uid in poll.polls


def test_poll_create_default(mock_bot: MockBot) -> None:
    poll.polls.clear()
    text = "thing?"
    conn = MockClient(bot=mock_bot)
    nick = "foo"
    chan = "#bar"
    event = MagicMock()
    message = event.message
    reply = event.reply
    uid = f"{conn.name}:{chan}:{nick}".lower()
    res = poll.poll(text, conn, nick, chan, message, reply)
    assert res is None
    assert event.mock_calls == [
        call.message(
            'Created poll \x02"thing?"\x02 with the following options: Yes and No'
        ),
        call.message("Use .vote foo <option> to vote on this poll!"),
    ]
    assert uid in poll.polls


def test_vote_invalid_input(mock_bot: MockBot) -> None:
    poll.polls.clear()
    text = "foo"
    conn = MockClient(bot=mock_bot)
    nick = "foo"
    chan = "#bar"
    event = MagicMock()
    notice = event.notice
    res = poll.vote(text, nick, conn, chan, notice)
    expected = (
        "Invalid input, please use .vote <user> <option> to vote on a poll."
    )
    assert res == expected
    assert event.mock_calls == []


def test_vote(mock_bot: MockBot) -> None:
    poll.polls.clear()
    text = "foo yes"
    conn = MockClient(bot=mock_bot)
    nick = "foo"
    chan = "#bar"
    uid = f"{conn.name}:{chan}:{nick}".lower()
    poll.polls[uid] = p = poll.Poll("foo?", "foo")
    event = MagicMock()
    notice = event.notice
    res = poll.vote(text, nick, conn, chan, notice)
    assert res is None
    assert event.mock_calls == [
        call.notice('Voted \x02"Yes"\x02 on foo\'s poll!')
    ]
    assert p.format_results() == "Yes: 1, No: 0"


def test_vote_unknown_opttion(mock_bot: MockBot) -> None:
    poll.polls.clear()
    text = "foo bar"
    conn = MockClient(bot=mock_bot)
    nick = "foo"
    chan = "#bar"
    uid = f"{conn.name}:{chan}:{nick}".lower()
    poll.polls[uid] = p = poll.Poll("foo?", "foo")
    event = MagicMock()
    notice = event.notice
    res = poll.vote(text, nick, conn, chan, notice)
    assert res == "Sorry, that's not a valid option for this poll."
    assert event.mock_calls == []
    assert p.format_results() == "Yes: 0, No: 0"


def test_vote_no_poll(mock_bot: MockBot) -> None:
    poll.polls.clear()
    text = "foo yes"
    conn = MockClient(bot=mock_bot)
    nick = "foo"
    chan = "#bar"
    event = MagicMock()
    notice = event.notice
    res = poll.vote(text, nick, conn, chan, notice)
    assert res == "Sorry, there is no active poll from that user."
    assert event.mock_calls == []


def test_results(mock_bot: MockBot) -> None:
    poll.polls.clear()
    text = ""
    conn = MockClient(bot=mock_bot)
    nick = "foo"
    chan = "#bar"
    uid = f"{conn.name}:{chan}:{nick}".lower()
    poll.polls[uid] = p = poll.Poll("foo?", nick)
    event = MagicMock()
    message = event.message
    reply = event.reply
    res = poll.results(text, conn, chan, nick, message, reply)
    assert res is None
    assert event.mock_calls == [
        call.reply('Results for \x02"foo?"\x02 by \x02foo\x02:'),
        call.message("Yes: 0, No: 0"),
    ]
    assert p.format_results() == "Yes: 0, No: 0"
