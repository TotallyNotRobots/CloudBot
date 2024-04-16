import socket
from unittest.mock import MagicMock, patch

import mcstatus
import pytest
from mcstatus.status_response import JavaStatusResponse

from plugins import minecraft_ping


@pytest.fixture()
def mock_mcserver():
    with patch.object(mcstatus.JavaServer, "lookup") as mock:
        yield mock


def test_mcping(mock_mcserver):
    mock_mcserver.return_value = server = MagicMock()
    server.status.return_value = JavaStatusResponse.build(
        {
            "version": {
                "name": "1.12.2",
                "protocol": 340,
            },
            "description": "A description",
            "players": {
                "online": 2,
                "max": 10,
            },
        },
        12.345,
    )
    res = minecraft_ping.mcping("host.invalid")
    assert (
        res
        == "A description\x0f - \x021.12.2\x0f - \x0212.3ms\x0f - \x022/10\x0f players"
    )


@pytest.mark.parametrize(
    "error,reply",
    [
        (IOError("Some IOError"), "Some IOError"),
        (ValueError("Some other ValueError"), "Some other ValueError"),
    ],
)
def test_mcping_lookup_errors(error, reply, mock_mcserver):
    mock_mcserver.side_effect = error
    res = minecraft_ping.mcping("host.invalid")

    assert res == reply


@pytest.mark.parametrize(
    "error,reply",
    [
        (socket.gaierror(2, "Foo"), "Invalid hostname"),
        (socket.timeout(), "Request timed out"),
        (ConnectionRefusedError(), "Connection refused"),
        (ConnectionError(), "Connection error"),
        (IOError("Some IOError"), "Error pinging server: Some IOError"),
        (
            ValueError("Some other ValueError"),
            "Error pinging server: Some other ValueError",
        ),
    ],
)
def test_mcping_status_errors(error, reply, mock_mcserver):
    mock_mcserver.return_value = server = MagicMock()
    server.status.side_effect = error
    res = minecraft_ping.mcping("host.invalid")

    assert res == reply
