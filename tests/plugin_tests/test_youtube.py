import pytest
from mock import MagicMock
from responses import RequestsMock

from cloudbot.bot import bot


@pytest.fixture()
def mock_requests():
    with RequestsMock() as reqs:
        yield reqs


@pytest.fixture()
def mock_api_keys():
    try:
        bot.set(MagicMock())
        bot.config.get_api_key.return_value = "APIKEY"
        yield
    finally:
        bot.set(None)


class TestGetVideoDescription:
    @staticmethod
    def test_no_key(mock_requests, mock_api_keys):
        from plugins import youtube

        mock_requests.add(
            'GET',
            'https://www.googleapis.com/youtube/v3/videos'
            '?part=contentDetails%2C+snippet%2C+statistics'
            '&id=foobar'
            '&key=APIKEY',
            match_querystring=True,
            json={'error': {'code': 403}},
            status=403,
        )

        with pytest.raises(youtube.APIError, match="YouTube API is off"):
            youtube.get_video_description('foobar')

    @staticmethod
    def test_http_error(mock_requests, mock_api_keys):
        from plugins import youtube

        mock_requests.add(
            'GET',
            'https://www.googleapis.com/youtube/v3/videos'
            '?part=contentDetails%2C+snippet%2C+statistics'
            '&id=foobar'
            '&key=APIKEY',
            match_querystring=True,
            json={'error': {'code': 500}},
            status=500,
        )

        with pytest.raises(youtube.APIError, match="Unknown error"):
            youtube.get_video_description('foobar')
