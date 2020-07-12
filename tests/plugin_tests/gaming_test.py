import random
from unittest.mock import MagicMock

import pytest

from cloudbot.event import CommandEvent
from plugins import gaming
from tests.util import wrap_hook_response


@pytest.mark.parametrize(
    "seed,n,result",
    [
        (1, 0, "makes a coin flipping motion"),
        (5, 1, "flips a coin and gets tails."),
        (84, 5, "flips 5 coins and gets 0 heads and 5 tails."),
        (5213, 21, "flips 21 coins and gets 5 heads and 16 tails."),
    ],
)
def test_coin(seed, n, result):
    random.seed(seed)

    event = CommandEvent(
        channel="#foo",
        text=str(n),
        triggered_command="coin",
        cmd_prefix=".",
        hook=MagicMock(),
        conn=MagicMock(),
    )
    res = wrap_hook_response(gaming.coin, event)
    assert res == [("action", ("#foo", result))]
