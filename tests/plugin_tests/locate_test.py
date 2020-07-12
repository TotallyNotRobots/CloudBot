from plugins import locate


def test_locate_no_key(mock_api_keys, mock_requests):
    mock_api_keys.return_value = None
    expected = "This command requires a Google Developers Console API key."
    assert locate.locate("foo") == expected


def test_locate_error(mock_api_keys, mock_requests):
    mock_requests.add(
        "GET",
        "https://maps.googleapis.com/maps/api/geocode/json?address=foo&key"
        "=APIKEY",
        status=400,
        json={"status": "REQUEST_DENIED"},
    )
    expected = "The geocode API is off in the Google Developers Console."
    assert locate.locate("foo") == expected
