import pytest

from cloudbot.util import pager


@pytest.mark.parametrize(
    "text,max_len,out",
    [
        (
            list("foobarbaz"),
            2,
            [
                ["f...", "o... (page 1/5)"],
                ["o...", "b... (page 2/5)"],
                ["a...", "r... (page 3/5)"],
                ["b...", "a... (page 4/5)"],
                ["z (page 5/5)"],
            ],
        ),
        (["abc", "def"], 256, [["abc \u2022 def"]]),
        (["abc", "def"], 5, [["abc...", "def"]]),
        (
            ["foo", "bar"],
            1,
            [
                ["f...", "o... (page 1/3)"],
                ["o...", "b... (page 2/3)"],
                ["a...", "r (page 3/3)"],
            ],
        ),
        (
            ["foo", "bar"],
            2,
            [["fo...", "o... (page 1/2)"], ["ba...", "r (page 2/2)"]],
        ),
    ],
)
def test_paginated_list(text, max_len, out):
    assert list(pager.paginated_list(text, max_len=max_len)) == out
