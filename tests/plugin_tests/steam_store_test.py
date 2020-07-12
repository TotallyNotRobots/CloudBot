from unittest.mock import MagicMock

from plugins import steam_store


def test_steam_no_results(mock_requests):
    mock_requests.add(
        "GET", "http://store.steampowered.com/search/?term=half+life"
    )
    reply = MagicMock()
    assert steam_store.steam("half life", reply) == "No game found."
    assert reply.mock_calls == []


def test_steam(mock_requests, patch_try_shorten):
    mock_requests.add(
        "GET",
        "http://store.steampowered.com/search/?term=half+life",
        body='<a data-ds-appid="546560" class="search_result_row '
        'ds_collapse_flag  app_impression_tracked"></a>',
    )
    mock_requests.add(
        "GET",
        "http://store.steampowered.com/api/appdetails/?appids=546560",
        json={
            "546560": {
                "data": {
                    "name": "Half Life",
                    "about_the_game": "foo",
                    "release_date": {
                        "coming_soon": False,
                        "date": "2020-05-02",
                    },
                    "is_free": True,
                    "steam_appid": "546560",
                }
            }
        },
    )
    reply = MagicMock()
    assert steam_store.steam("half life", reply) == (
        "\x02Half Life\x02 - foo - released \x022020-05-02\x02 - \x02free\x02 "
        "- http://store.steampowered.com/app/546560/"
    )
    assert reply.mock_calls == []
