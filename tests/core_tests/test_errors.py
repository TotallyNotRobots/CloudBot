import re

import pytest

from cloudbot.errors import ShouldBeUnreachable


def test_should_be_unreachable() -> None:
    with pytest.raises(
        ShouldBeUnreachable,
        match=re.escape(
            f"A branch that should be unreachable has been reached at {__file__}:17. "
            "THIS IS A BUG. Please report it right away on the issue tracker at "
            "https://github.com/TotallyNotRobots/CloudBot/issues/new"
        ),
    ):
        raise ShouldBeUnreachable
