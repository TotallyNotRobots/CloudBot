from unittest.mock import MagicMock, call

from plugins import linux


def test_linux(mock_requests):
    mock_requests.add(
        "GET",
        "https://www.kernel.org/finger_banner",
        body="""\
The latest stable version of the Linux kernel is:             5.11.2
The latest mainline version of the Linux kernel is:           5.12-rc1
The latest stable 5.11 version of the Linux kernel is:        5.11.2
The latest longterm 5.10 version of the Linux kernel is:      5.10.19
The latest longterm 5.4 version of the Linux kernel is:       5.4.101
The latest longterm 4.19 version of the Linux kernel is:      4.19.177
The latest longterm 4.14 version of the Linux kernel is:      4.14.222
The latest longterm 4.9 version of the Linux kernel is:       4.9.258
The latest longterm 4.4 version of the Linux kernel is:       4.4.258
The latest linux-next version of the Linux kernel is:         next-20210226
        """.strip(),
    )
    event = MagicMock()
    res = linux.kernel(event.reply)
    assert res is None
    assert event.mock_calls == [
        call.reply(
            "Linux kernel versions: stable - 5.11.2, mainline - 5.12-rc1, stable 5.11 - 5.11.2, longterm 5.10 - 5.10.19, longterm 5.4 - 5.4.101, longterm 4.19 - 4.19.177, longterm 4.14 - 4.14.222, longterm 4.9 - 4.9.258, longterm 4.4 - 4.4.258"
        )
    ]
