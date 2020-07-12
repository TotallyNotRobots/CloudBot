import pytest

from plugins import imgur


@pytest.fixture()
def unset_api():
    try:
        yield
    finally:
        imgur.container.api = None


def test_imgur_no_api(mock_requests, mock_api_keys):
    assert imgur.imgur("foo") == "No imgur API details"


def test_imgur_api_credits(mock_requests, mock_api_keys, unset_api):
    headers = {
        "X-RateLimit-UserLimit": "5",
        "X-RateLimit-UserRemaining": "2",
        "X-RateLimit-UserReset": "123456",
        "X-RateLimit-ClientLimit": "456",
        "X-RateLimit-ClientRemaining": "123",
    }
    mock_requests.add(
        "GET",
        "https://api.imgur.com/3/credits",
        adding_headers=headers,
        json={
            "UserLimit": headers.get("X-RateLimit-UserLimit"),
            "UserRemaining": headers.get("X-RateLimit-UserRemaining"),
            "UserReset": headers.get("X-RateLimit-UserReset"),
            "ClientLimit": headers.get("X-RateLimit-ClientLimit"),
            "ClientRemaining": headers.get("X-RateLimit-ClientRemaining"),
        },
    )
    imgur.set_api()
    assert imgur.imgur("apicredits") == {
        "ClientLimit": "456",
        "ClientRemaining": "123",
        "UserLimit": "5",
        "UserRemaining": "2",
        "UserReset": "123456",
    }
