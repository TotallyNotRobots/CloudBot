import json

from plugins import validate
from tests.util import get_test_data


def test_validate(mock_requests, patch_try_shorten):
    mock_requests.add(
        "GET",
        "https://validator.w3.org/nu/?doc=http%3A%2F%2Fyoutube.com&out=json",
        json=json.loads(get_test_data("validator.json")),
    )

    expected = (
        "http://youtube.com has 1 warning and 18 errors ("
        "https://validator.w3.org/nu/?doc=http://youtube.com)"
    )
    assert validate.validate("youtube.com") == expected
