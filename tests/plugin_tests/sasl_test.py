from unittest.mock import MagicMock

import pytest

from plugins.core import sasl


@pytest.mark.parametrize(
    "config,enabled",
    [
        ({}, False),
        ({"sasl": {}}, False),
        ({"sasl": {"pass": "password"}}, True),
        ({"sasl": {"enabled": True}}, True),
        ({"sasl": {"enabled": False}}, False),
    ],
)
def test_sasl_available(config, enabled):
    conn = MagicMock()
    conn.mock_add_spec(["config"], spec_set=True)
    conn.config = config

    assert sasl.sasl_available(conn) == enabled
