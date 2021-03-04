from unittest.mock import MagicMock, call, patch

import pytest

from plugins import ping


@pytest.fixture()
def patch_subproc():
    with patch("subprocess.check_output") as mocked:
        yield mocked


def test_ping(patch_subproc):
    with patch.object(ping, "IS_WINDOWS", new=False):
        patch_subproc.return_value = b"""\
PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
64 bytes from 1.1.1.1: icmp_seq=1 ttl=56 time=14.6 ms
64 bytes from 1.1.1.1: icmp_seq=2 ttl=56 time=11.9 ms
64 bytes from 1.1.1.1: icmp_seq=3 ttl=56 time=11.4 ms
64 bytes from 1.1.1.1: icmp_seq=4 ttl=56 time=11.5 ms
64 bytes from 1.1.1.1: icmp_seq=5 ttl=56 time=13.5 ms

--- 1.1.1.1 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4007ms
rtt min/avg/max/mdev = 11.403/12.584/14.632/1.270 ms
"""
        event = MagicMock()
        res = ping.ping("1.1.1.1 5", event.reply)
        assert patch_subproc.mock_calls == [
            call(["ping", "-c", "5", "1.1.1.1"])
        ]
        assert event.mock_calls == [
            call.reply("Attempting to ping 1.1.1.1 5 times...")
        ]
        expted = "min: 11.403ms, max: 14.632ms, average: 12.584ms, range: 1.270ms, count: 5"
        assert res == expted


def test_ping_win(patch_subproc):
    with patch.object(ping, "IS_WINDOWS", new=True):
        patch_subproc.return_value = b"""\
PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
64 bytes from 1.1.1.1: icmp_seq=1 ttl=56 time=14.6 ms
64 bytes from 1.1.1.1: icmp_seq=2 ttl=56 time=11.9 ms
64 bytes from 1.1.1.1: icmp_seq=3 ttl=56 time=11.4 ms
64 bytes from 1.1.1.1: icmp_seq=4 ttl=56 time=11.5 ms
64 bytes from 1.1.1.1: icmp_seq=5 ttl=56 time=13.5 ms

--- 1.1.1.1 ping statistics ---
Minimum = 5ms, Maximum = 10ms, Average = 7ms
"""
        event = MagicMock()
        res = ping.ping("1.1.1.1 5", event.reply)
        assert patch_subproc.mock_calls == [
            call(["ping", "-n", "5", "1.1.1.1"])
        ]
        assert event.mock_calls == [
            call.reply("Attempting to ping 1.1.1.1 5 times...")
        ]
        assert res == "min: 5ms, max: 10ms, average: 7ms, range: 5ms, count: 5"
