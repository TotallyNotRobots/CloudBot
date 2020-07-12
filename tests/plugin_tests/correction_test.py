from unittest.mock import MagicMock

import pytest

from cloudbot.event import RegexEvent
from plugins import correction
from tests.util import wrap_hook_response


@pytest.mark.parametrize(
    "text,pattern,output",
    [
        (
            "foo",
            "s/f/g",
            [("message", ("#foochan", "Correction, <foonick> \x02g\x02oo"))],
        ),
        (
            "\1ACTIONfoobar",
            "s/f/g",
            [("message", ("#foochan", "Correction, * foonick \x02g\x02oobar"))],
        ),
        (
            "\1ACTION foobar",
            "s/f/g",
            [("message", ("#foochan", "Correction, * foonick \x02g\x02oobar"))],
        ),
        (
            "foo",
            "s//g",
            [("return", "really dude? you want me to replace nothing with g?")],
        ),
        (
            "foo",
            "s/f/f",
            [("return", "really dude? you want me to replace f with f?")],
        ),
        ("s/a/b", "s/a/b", []),
    ],
)
def test_correction(text, pattern, output):
    conn = MagicMock(history={"#foochan": [("foonick", 1, text),]})

    match = correction.correction_re.search(pattern)
    event = RegexEvent(
        match=match,
        conn=conn,
        hook=MagicMock(),
        nick="foonick",
        channel="#foochan",
    )

    assert wrap_hook_response(correction.correction, event) == output
