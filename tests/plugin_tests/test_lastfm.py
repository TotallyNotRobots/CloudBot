from json import JSONDecodeError

import pytest
import requests
from requests import HTTPError
from responses import RequestsMock

from cloudbot.bot import bot
from cloudbot.config import Config
from plugins.lastfm import api_request


class MockConfig(Config):
    def load_config(self):
        self._api_keys.clear()


class MockBot:
    def __init__(self, config):
        self.config = MockConfig(self, config)


def test_api(unset_bot):
    bot.set(MockBot({"api_keys": {"lastfm": "hunter20"}}))

    with RequestsMock() as reqs:
        with pytest.raises(requests.ConnectionError):
            api_request("track.getTopTags")

        reqs.add(reqs.GET, "http://ws.audioscrobbler.com/2.0/", json={"data": "thing"})

        res, _ = api_request("track.getTopTags")

        assert res["data"] == "thing"

    with RequestsMock() as reqs:
        reqs.add(reqs.GET, "http://ws.audioscrobbler.com/2.0/", body="<html></html>")

        with pytest.raises(JSONDecodeError):
            api_request("track.getTopTags")

    with RequestsMock() as reqs:
        reqs.add(
            reqs.GET,
            "http://ws.audioscrobbler.com/2.0/",
            body="<html></html>",
            status=403,
        )

        with pytest.raises(HTTPError):
            api_request("track.getTopTags")
