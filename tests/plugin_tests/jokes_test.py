import random
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from plugins import jokes
from tests.util.mock_conn import MockConn


def test_load_jokes(mock_bot_factory):
    mock_bot = mock_bot_factory(
        base_dir=Path(__file__).parent.parent.parent.resolve()
    )
    jokes.load_jokes(mock_bot)


def test_lawuerjoke():
    jokes.joke_lines.clear()
    jokes.joke_lines["lawyerjoke"] = ["foobar"]
    event = MagicMock()
    res = jokes.lawyerjoke(event.message)
    assert res is None
    assert event.mock_calls == [call.message("foobar")]


def test_doit():
    jokes.joke_lines.clear()
    jokes.joke_lines["do_it"] = ["foobar"]
    event = MagicMock()
    res = jokes.doit(event.message)
    assert res is None
    assert event.mock_calls == [call.message("foobar")]


def test_puns():
    jokes.joke_lines.clear()
    jokes.joke_lines["puns"] = ["foobar"]
    event = MagicMock()
    res = jokes.pun(event.message)
    assert res is None
    assert event.mock_calls == [call.message("foobar")]


def test_confucious():
    jokes.joke_lines.clear()
    jokes.joke_lines["confucious"] = ["foobar"]
    event = MagicMock()
    res = jokes.confucious(event.message)
    assert res is None
    assert event.mock_calls == [call.message("Confucious say foobar")]


def test_yo_mamma():
    jokes.joke_lines.clear()
    jokes.joke_lines["yo_momma"] = ["foobar"]
    event = MagicMock()
    event.is_nick_valid.return_value = True
    nick = "foo"
    conn = MockConn()
    text = "bar"
    res = jokes.yomomma(text, nick, conn, event.is_nick_valid)
    assert res == "bar, foobar"
    assert event.mock_calls == [call.is_nick_valid("bar")]


def test_dadjokes():
    jokes.joke_lines.clear()
    jokes.joke_lines["one_liners"] = ["foobar"]
    event = MagicMock()
    res = jokes.dadjoke(event.message)
    assert res is None
    assert event.mock_calls == [call.message("foobar")]


def test_wisdom():
    jokes.joke_lines.clear()
    jokes.joke_lines["wisdom"] = ["foobar"]
    event = MagicMock()
    res = jokes.wisdom(event.message)
    assert res is None
    assert event.mock_calls == [call.message("foobar")]


def test_bookpun():
    jokes.joke_lines.clear()
    jokes.joke_lines["book_puns"] = ["foobar"]
    event = MagicMock()
    res = jokes.bookpun(event.message)
    assert res is None
    assert event.mock_calls == [call.message("foobar")]


@pytest.mark.parametrize(
    "text,out",
    [
        (
            "test",
            "Sorry I couldn't turn anything in 'test' into boobs for you.",
        ),
        ("foobar", "f⊙⊙bar"),
        ("", "Sorry I couldn't turn anything in '' into boobs for you."),
    ],
)
def test_boobies(text, out):
    assert jokes.boobies(text) == out


def test_awesome():
    res = jokes.awesome("foo", lambda text: True)
    assert res == (
        "foo: I am blown away by your recent awesome action(s). Please read "
        "\x02http://foo.is-awesome.cool/\x02"
    )


def test_awesome_bad_nick():
    res = jokes.awesome("foo", lambda text: False)
    assert res == "Sorry I can't tell foo how awesome they are."


def test_triforce():
    random.seed(0)
    event = MagicMock()
    res = jokes.triforce(event.message)
    assert res is None
    assert event.mock_calls == [call.message("\xa0▲"), call.message("▲ ▲")]


def test_kero():
    jokes.joke_lines.clear()
    jokes.joke_lines["kero"] = ["foobar"]
    res = jokes.kero("barfoo")
    assert res == "BARFOO FOOBAR"
