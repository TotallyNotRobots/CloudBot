import random
from unittest.mock import MagicMock, call

import pytest

from plugins import flip


@pytest.mark.parametrize(
    "text,chan,calls",
    [
        (
            "table",
            "#fpp",
            [
                call.message(
                    "\u253b\u2501\u253b \ufe35\u30fd(`"
                    "\u0414\xb4)\uff89\ufe35 \u253b\u2501\u253b"
                )
            ],
        ),
        (
            "tables",
            "#fpp",
            [
                call.message(
                    "\u253b\u2501\u253b \ufe35\u30fd(`"
                    "\u0414\xb4)\uff89\ufe35 \u253b\u2501\u253b"
                )
            ],
        ),
        (
            "foobar",
            "#fpp",
            [
                call.message(
                    "(\u256f\xb0\u25a1\xb0\uff09"
                    "\u256f \ufe35 \u0279\u0250qoo\u025f"
                )
            ],
        ),
        (
            "5318008",
            "#fpp",
            [call.message("(\u256f\xb0\u25a1\xb0\uff09\u256f \ufe35 BOOBIES")],
        ),
        (
            "BOOBIES",
            "#fpp",
            [call.message("(\u256f\xb0\u25a1\xb0\uff09\u256f \ufe35 5318008")],
        ),
    ],
)
def test_flip(text, chan, calls):
    random.seed(0)
    event = MagicMock()
    assert flip.flip(text, event.message, chan) is None
    assert event.mock_calls == calls


@pytest.mark.parametrize(
    "text,calls",
    [
        (
            "table",
            [
                call.message(
                    "(\u256f\xb0\u25a1\xb0"
                    "\uff09\u256f \ufe35 \u01dd\u05dfq\u0250\u0287"
                )
            ],
        ),
        (
            "tables",
            [
                call.message(
                    "(\u256f\xb0\u25a1\xb0\uff09\u256f "
                    "\ufe35 s\u01dd\u05dfq\u0250\u0287"
                )
            ],
        ),
        (
            "foobar",
            [
                call.message(
                    "(\u256f\xb0\u25a1\xb0\uff09\u256f"
                    " \ufe35 \u0279\u0250qoo\u025f"
                )
            ],
        ),
    ],
)
def test_table(text, calls):
    random.seed(0)
    event = MagicMock()
    assert flip.table(text, event.message) is None
    assert event.mock_calls == calls


def test_fix_flipped():
    event = MagicMock()
    flip.table_status["#foo"] = True
    assert flip.fix("table", event.message, "#foo") is None
    assert event.mock_calls == [call.message(flip.FIXED_TABLE)]


def test_fix():
    event = MagicMock()
    assert flip.fix("table", event.message, "#foo") is None
    assert event.mock_calls == [
        call.message(
            "no tables have been turned over in #foo, thanks for checking!"
        )
    ]


def test_fix_other():
    random.seed(0)
    event = MagicMock()
    assert flip.fix("foo", event.message, "#foo") is None
    assert event.mock_calls == [
        call.message("(\u256f\xb0\u25a1\xb0\uff09\u256f \ufe35 oo\u025f")
    ]
