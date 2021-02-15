import random
from unittest.mock import MagicMock, call, patch

from plugins import fact


def test_fact():
    random.seed(0)
    with patch("cloudbot.util.http.get_json") as mocked:
        mocked.return_value = {"text": "foobar"}
        reply = MagicMock()
        assert fact.fact(reply) == "foobar"
        assert mocked.mock_calls == [
            call("http://numbersapi.com/random/year?json")
        ]
