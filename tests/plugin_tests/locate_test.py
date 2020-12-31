import pytest

from plugins import locate


@pytest.mark.parametrize(
    "status,out",
    [
        (
            "REQUEST_DENIED",
            "The geocode API is off in the Google Developers Console.",
        ),
        ("ZERO_RESULTS", "No results found."),
        ("OVER_QUERY_LIMIT", "The geocode API quota has run out."),
        ("UNKNOWN_ERROR", "Unknown Error."),
        ("INVALID_REQUEST", "Invalid Request."),
        ("OK", None),
        ("foobar", None),
    ],
)
def test_check_status(status, out):
    assert locate.check_status(status) == out
