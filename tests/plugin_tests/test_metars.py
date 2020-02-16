def test_metars(mock_requests):
    mock_requests.add(
        mock_requests.GET,
        "http://api.av-wx.com/metar/ABCD",
        json={"reports": [{"name": "ABCD", "raw_text": "Foo Bar Test"}]},
    )
    from plugins.metars import metar

    assert metar("abcd") == "ABCD: Foo Bar Test"


def test_taf(mock_requests):
    mock_requests.add(
        mock_requests.GET,
        "http://api.av-wx.com/taf/ABCD",
        json={"reports": [{"name": "ABCD", "raw_text": "Foo Bar Test"}]},
    )
    from plugins.metars import taf

    assert taf("abcd") == "ABCD: Foo Bar Test"


def test_invalid_station(mock_requests):
    from plugins.metars import taf

    invalid_station = (
        "please specify a valid station code "
        "see http://weather.rap.ucar.edu/surface/stations.txt "
        "for a list."
    )
    assert taf("abc") == invalid_station


def test_station_not_found(mock_requests):
    mock_requests.add(
        mock_requests.GET, "http://api.av-wx.com/taf/ABCD", json={}, status=404,
    )
    from plugins.metars import taf

    assert taf("abcd") == "Station not found"
