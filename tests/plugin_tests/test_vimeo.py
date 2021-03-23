from copy import deepcopy
from unittest.mock import patch

import pytest

from plugins import vimeo


@pytest.fixture()
def patch_get_json():
    with patch("cloudbot.util.http.get_json") as patched:
        yield patched


DATA = [
    {
        "id": 11235,
        "title": "A video title",
        "description": "Some video description",
        "url": "https://vimeo.com/112345",
        "upload_date": "2006-10-24 22:56:45",
        "user_id": 554,
        "user_name": "AUser",
        "user_url": "https://vimeo.com/user554",
        "stats_number_of_plays": 106,
        "stats_number_of_comments": 6,
        "duration": 44,
        "width": 320,
        "height": 240,
        "tags": "foo, bar",
        "embed_privacy": "anywhere",
    }
]


def test_no_data(patch_get_json):
    patch_get_json.return_value = []

    result = vimeo.vimeo_url(vimeo.url_re.search("https://vimeo.com/1125483"))

    assert result is None


def test_no_likes(patch_get_json):
    patch_get_json.return_value = deepcopy(DATA)

    result = vimeo.vimeo_url(vimeo.url_re.search("https://vimeo.com/11235"))

    expected_parts = [
        "\x02A video title\x02",
        "length \x0244 seconds\x02",
        "\x020\x02 likes",
        "\x02106\x02 plays",
        "\x02AUser\x02 on \x022006-10-24 22:56:45\x02",
    ]

    expected = " - ".join(expected_parts)

    assert result == expected


def test_with_likes(patch_get_json):
    data = deepcopy(DATA)

    data[0]["stats_number_of_likes"] = 54

    patch_get_json.return_value = data

    result = vimeo.vimeo_url(vimeo.url_re.search("https://vimeo.com/11235"))

    expected_parts = [
        "\x02A video title\x02",
        "length \x0244 seconds\x02",
        "\x0254\x02 likes",
        "\x02106\x02 plays",
        "\x02AUser\x02 on \x022006-10-24 22:56:45\x02",
    ]

    expected = " - ".join(expected_parts)

    assert result == expected
