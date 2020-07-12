import importlib

from plugins import time_plugin
from tests.util import run_cmd


def test_time(mock_requests, mock_api_keys, freeze_time):
    importlib.reload(time_plugin)
    mock_requests.add(
        "GET",
        "https://maps.googleapis.com/maps/api/geocode/json?address=new+york"
        "&key=APIKEY",
        match_querystring=True,
        json={
            "status": "OK",
            "results": [
                {
                    "formatted_address": "foo addr",
                    "geometry": {"location": {"lat": 50, "lng": 74}},
                }
            ],
        },
    )
    mock_requests.add(
        "GET",
        "https://maps.googleapis.com/maps/api/timezone/json?location=50%2C74"
        "&timestamp=1566497676.0&key=APIKEY",
        match_querystring=True,
        json={
            "status": "OK",
            "rawOffset": -5,
            "dstOffset": 1,
            "timeZoneName": "newyork",
        },
    )
    assert run_cmd(time_plugin.time_command, "time", "new york") == [
        (
            "return",
            "\x0206:14 PM, Thursday, August 22, 2019\x02 - foo addr (newyork)",
        )
    ]
