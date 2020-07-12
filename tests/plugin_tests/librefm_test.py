import importlib

from plugins import librefm
from tests.util import run_cmd


def test_librefm_bad_args(mock_requests, reset_database):
    importlib.reload(librefm)
    res = run_cmd(librefm.librefm, "librefm", "")
    assert res == [
        (
            "message",
            (
                "foonick",
                ".librefm [user] [dontsave] - displays the now playing (or "
                "last played) track of libre.fm user [user]",
            ),
        )
    ]


def test_librefm_http_error(mock_requests, reset_database):
    importlib.reload(librefm)
    mock_requests.add(
        "GET",
        "https://libre.fm/2.0/?format=json&user=foo&limit=1&method=user"
        ".getrecenttracks",
        status=400,
    )
    res = run_cmd(librefm.librefm, "librefm", "foo")
    assert res == [("return", "Failed to fetch info (400)")]


def test_librefm_api_error(mock_requests, reset_database):
    importlib.reload(librefm)
    mock_requests.add(
        "GET",
        "https://libre.fm/2.0/?format=json&user=foo&limit=1&method=user"
        ".getrecenttracks",
        json={"error": {"#text": "foo", "code": 500,}},
    )
    res = run_cmd(librefm.librefm, "librefm", "foo")
    assert res == [("return", "libre.fm Error: foo Code: 500.")]
