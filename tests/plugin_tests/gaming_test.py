import random
from unittest.mock import MagicMock, call

import pytest

from plugins import gaming


@pytest.mark.parametrize(
    "text,out",
    [
        ("d5", "2 (2)"),
        ("2d5+3", "10 (2, 5)"),
        ("2d5+3d5", "12 (2, 5, 1, 3, 1)"),
        ("2d5+3d5-2", "10 (2, 5, 1, 3, 1)"),
        (
            "99d99",
            (
                "5381 (18, 73, 98, 9, 33, 16, 64, 98, 58, 61, 84, 49, 27, 13, 63, 4, 50, 56, "
                "78, 98, 99, 1, 90, 58, 35, 93, 30, 76, 14, 41, 4, 3, 4, 84, 70, 2, 49, 88, "
                "28, 55, 93, 4, 68, 29, 98, 57, 64, 71, 30, 45, 30, 87, 29, 98, 59, 38, 3, "
                "54, 72, 83, 13, 24, 81, 93, 38, 16, 96, 43, 93, 92, 65, 55, 65, 86, 25, 39, "
                "37, 76, 64, 65, 51, 76, 5, 62, 32, 96, 52, 54, 86, 23, 47, 71, 90, 87, 95, "
                "48, 12, 57, 85)"
            ),
        ),
        ("4df", "-1 (\x034-\x0f, \x033+\x0f, \x034-\x0f, 0)"),
        ("100d100", "5225 (5225)"),
        ("100d100 some text", "some text: 5225 (5225)"),
        ("-3d4", "-6 (-2, -1, -3)"),
        (
            "15df",
            (
                "-4 (\x034-\x0f, \x033+\x0f, \x034-\x0f, 0, \x034-\x0f, 0, 0, 0, \x033+\x0f, "
                "0, \x034-\x0f, \x034-\x0f, 0, \x034-\x0f, 0)"
            ),
        ),
    ],
)
def test_dice(text, out):
    random.seed(1)
    event = MagicMock()
    res = gaming.dice(text, event)
    assert res == out
    assert event.mock_calls == []


def test_dice_overflow():
    random.seed(1)
    event = MagicMock()
    with pytest.raises(OverflowError):
        gaming.dice((str(10**308)) + "d9", event)

    assert event.mock_calls == [
        call.reply("Thanks for overflowing a float, jerk >:[")
    ]


def test_dice_bad_input():
    event = MagicMock()
    res = gaming.dice("something", event)
    assert res is None
    assert event.mock_calls == [call.notice("Invalid dice roll 'something'")]


def test_dice_num_only():
    event = MagicMock()
    res = gaming.dice("6", event)
    assert res is None
    assert event.mock_calls == []


@pytest.mark.parametrize(
    "text,out",
    [
        ("a or b", "a"),
        ("a, b", "a"),
        ("a,b,c", "a"),
    ],
)
def test_choose(text, out):
    random.seed(1)
    event = MagicMock()
    assert gaming.choose(text, event) == out
    assert event.mock_calls == []


@pytest.mark.parametrize(
    "text,out,seed",
    [
        ("", [call.action("flips a coin and gets heads.")], 4),
        ("a", [call.notice("Invalid input 'a': not a number")], 4),
        (
            "12",
            [call.action("flips 12 coins and gets 4 heads and 8 tails.")],
            4,
        ),
        ("0", [call.action("makes a coin flipping motion")], 4),
        (
            "9999",
            [
                call.action(
                    "flips 9999 coins and gets 4956 heads and 5043 tails."
                )
            ],
            4,
        ),
    ],
)
def test_coin(text, out, seed):
    random.seed(seed)
    event = MagicMock()
    res = gaming.coin(text, event.notice, event.action)
    assert res is None
    assert event.mock_calls == out
