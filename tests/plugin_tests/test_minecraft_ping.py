import socket
from unittest.mock import MagicMock, patch

import mcstatus
import pytest

from plugins import minecraft_ping


@pytest.fixture()
def mock_mcserver():
    with patch.object(mcstatus.MinecraftServer, "lookup") as mock:
        yield mock


def test_mcping(mock_mcserver):
    mock_mcserver.return_value = server = MagicMock()
    server.status.return_value = status = MagicMock()
    status.version.name = "1.12.2"
    status.latency = 12.345
    status.players.online = 2
    status.players.max = 10
    status.description = {"text": "A description"}
    res = minecraft_ping.mcping("host.invalid")
    assert (
        res
        == "A description\x0f - \x021.12.2\x0f - \x0212.3ms\x0f - \x022/10\x0f players"
    )


def test_mcping_text(mock_mcserver):
    mock_mcserver.return_value = server = MagicMock()
    server.status.return_value = status = MagicMock()
    status.version.name = "1.12.2"
    status.latency = 12.345
    status.players.online = 2
    status.players.max = 10
    status.description = "A description"
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
