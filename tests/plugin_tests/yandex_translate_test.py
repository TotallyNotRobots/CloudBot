from plugins import yandex_translate


def test_load_key(mock_requests, mock_api_keys):
    mock_requests.add(
        "GET",
        "https://translate.yandex.net/api/v1.5/tr.json/getLangs?key=APIKEY&ui"
        "=en",
        match_querystring=True,
        json={
            "dirs": ["en-ru", "en-pl", "en-hu",],
            "langs": {"en": "English", "ru": "Russian", "pl": "Polish",},
        },
    )
    yandex_translate.load_key()
    assert yandex_translate.lang_dict == {
        "English": "en",
        "Polish": "pl",
        "Russian": "ru",
    }
    assert yandex_translate.lang_dir == ["en-ru", "en-pl", "en-hu"]
