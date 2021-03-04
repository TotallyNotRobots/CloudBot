from pathlib import Path

import pytest

from plugins import foaas


@pytest.mark.parametrize(
    "fucker,fuckee,out",
    [
        ("foo", None, "http://www.foaas.com/bar/foo"),
        ("foo", "bar", "http://www.foaas.com/foo/\x02bar\x02/foo"),
    ],
)
def test_format_url(fucker, fuckee, out):
    foaas.fuck_offs["fuck_offs"] = ["foo"]
    foaas.fuck_offs["single_fucks"] = ["bar"]
    assert foaas.format_url(fucker, fuckee) == out


def test_load_data(mock_bot_factory):
    mock_bot = mock_bot_factory(base_dir=Path().resolve())
    res = foaas.load_fuck_offs(mock_bot)
    assert res is None
    assert foaas.fuck_offs == {
        "fuck_offs": [
            "donut",
            "bus",
            "chainsaw",
            "king",
            "madison",
            "gfy",
            "back",
            "keep",
            "name",
            "bday",
            "dalton",
            "ing",
            "nugget",
            "outside",
            "off",
            "problem",
            "shakespeare",
            "think",
            "thinking",
            "xmas",
            "yoda",
            "you",
        ],
        "single_fucks": [
            "bag",
            "awesome",
            "because",
            "bucket",
            "bye",
            "cool",
            "everyone",
            "everything",
            "flying",
            "give",
            "horse",
            "life",
            "looking",
            "maybe",
            "me",
            "mornin",
            "no",
            "pink",
            "retard",
            "rtfm",
            "sake",
            "shit",
            "single",
            "thanks",
            "that",
            "this",
            "too",
            "tucker",
            "zayn",
            "zero",
        ],
    }
