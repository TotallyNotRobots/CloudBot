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
    base_url = 'https://www.googleapis.com/youtube/v3/'
    api_url = base_url + (
        'videos?part=contentDetails%2C+snippet%2C+statistics&id={id}&key={key}'
    )
    search_api_url = base_url + 'search?part=id&maxResults=1'

    def test_no_key(self, mock_requests, mock_api_keys):
        from plugins import youtube

        mock_requests.add(
            'GET',
            self.api_url.format(id='foobar', key='APIKEY'),
            match_querystring=True,
            json={'error': {'code': 403}},
            status=403,
        )

        with pytest.raises(youtube.APIError, match="YouTube API is off"):
            youtube.get_video_description('foobar')

    def test_http_error(self, mock_requests, mock_api_keys):
        from plugins import youtube

        mock_requests.add(
            'GET',
            self.api_url.format(id='foobar', key='APIKEY'),
            match_querystring=True,
            json={'error': {'code': 500}},
            status=500,
        )

        with pytest.raises(youtube.APIError, match="Unknown error"):
            youtube.get_video_description('foobar')

    def test_command_error_reply(self, mock_requests, mock_api_keys):
        from plugins import youtube

        mock_requests.add(
            'GET',
            'https://www.googleapis.com/youtube/v3/search',
            json={
                'items': [{
                    'id': {'videoId': 'foobar'},
                }],
                'pageInfo': {'totalResults': 1},
            },
        )

        mock_requests.add(
            'GET',
            self.api_url.format(id='foobar', key='APIKEY'),
            match_querystring=True,
            json={'error': {'code': 500}},
            status=500,
        )

        reply = MagicMock()

        with pytest.raises(youtube.APIError):
            youtube.youtube('test video', reply)

        reply.assert_called_with("Unknown error")
