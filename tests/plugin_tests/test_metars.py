from plugins import metars


def test_metars(mock_requests):
    mock_requests.add(
        "GET",
        "http://api.av-wx.com/metar/ABCD",
        json={"reports": [{"name": "ABCD", "raw_text": "Foo Bar Test"}]},
    )

    assert metars.metar("abcd") == "ABCD: Foo Bar Test"


def test_taf(mock_requests):
    mock_requests.add(
        "GET",
        "http://api.av-wx.com/taf/ABCD",
        json={"reports": [{"name": "ABCD", "raw_text": "Foo Bar Test"}]},
    )
    assert metars.taf("abcd") == "ABCD: Foo Bar Test"


def test_invalid_station(mock_requests):
    invalid_station = (
        "please specify a valid station code "
        "see http://weather.rap.ucar.edu/surface/stations.txt "
        "for a list."
    )
    assert metars.taf("abc") == invalid_station


def test_station_not_found(mock_requests):
    mock_requests.add(
        "GET",
        "http://api.av-wx.com/taf/ABCD",
        json={},
        status=404,
    )
    assert metars.taf("abcd") == "Station not found"
