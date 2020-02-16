from copy import deepcopy
from unittest.mock import MagicMock

import pytest
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


video_data = {
    "kind": "youtube#videoListResponse",
    "etag": '"p4VTdlkQv3HQeTEaXgvLePAydmU/Lj2TyUBAY4pSJv0nR-wZBKBK9YU"',
    "pageInfo": {"totalResults": 1, "resultsPerPage": 1},
    "items": [
        {
            "kind": "youtube#video",
            "etag": '"p4VTdlkQv3HQeTEaXgvLePAydmU/8GTj_EHYgQmPYCDpJbQ4NM6r5B8"',
            "id": "phL7P6gtZRM",
            "snippet": {
                "publishedAt": "2019-10-10T15:00:09.000Z",
                "channelId": "UCRUULstZRWS1lDvJBzHnkXA",
                "title": "some title",
                "description": "a description",
                "thumbnails": {},
                "channelTitle": "a channel",
                "tags": ["a tag"],
                "categoryId": "24",
                "liveBroadcastContent": "none",
                "localized": {"title": "some title", "description": "a description"},
                "defaultAudioLanguage": "en",
            },
            "contentDetails": {
                "duration": "PT17M2S",
                "dimension": "2d",
                "definition": "hd",
                "caption": "true",
                "licensedContent": True,
                "projection": "rectangular",
            },
            "statistics": {
                "viewCount": "68905",
                "likeCount": "4633",
                "dislikeCount": "31",
                "favoriteCount": "0",
                "commentCount": "536",
            },
        }
    ],
}


class TestGetVideoDescription:
    base_url = "https://www.googleapis.com/youtube/v3/"
    api_url = base_url + (
        "videos?part=contentDetails%2C+snippet%2C+statistics&id={id}&key={key}"
    )
    search_api_url = base_url + "search?part=id&maxResults=1"

    def test_no_key(self, mock_requests, mock_api_keys):
        from plugins import youtube

        mock_requests.add(
            "GET",
            self.api_url.format(id="foobar", key="APIKEY"),
            match_querystring=True,
            json={"error": {"code": 403}},
            status=403,
        )

        with pytest.raises(youtube.APIError, match="YouTube API is off"):
            youtube.get_video_description("foobar")

    def test_http_error(self, mock_requests, mock_api_keys):
        from plugins import youtube

        mock_requests.add(
            "GET",
            self.api_url.format(id="foobar", key="APIKEY"),
            match_querystring=True,
            json={"error": {"code": 500}},
            status=500,
        )

        with pytest.raises(youtube.APIError, match="Unknown error"):
            youtube.get_video_description("foobar")

    def test_success(self, mock_requests, mock_api_keys):
        from plugins import youtube

        mock_requests.add(
            "GET",
            self.api_url.format(id="phL7P6gtZRM", key="APIKEY"),
            match_querystring=True,
            json=video_data,
        )

        result = (
            "\x02some title\x02 - length \x0217m 2s\x02 - "
            "4,633 likes, 31 dislikes (\x0299.3\x02%) - "
            "\x0268,905\x02 views - \x02a channel\x02 on \x022019.10.10\x02"
        )

        assert youtube.get_video_description("phL7P6gtZRM") == result

    def test_success_no_duration(self, mock_requests, mock_api_keys):
        from plugins import youtube

        data = deepcopy(video_data)
        del data["items"][0]["contentDetails"]["duration"]

        mock_requests.add(
            "GET",
            self.api_url.format(id="phL7P6gtZRM", key="APIKEY"),
            match_querystring=True,
            json=data,
        )

        result = "\x02some title\x02"

        assert youtube.get_video_description("phL7P6gtZRM") == result

    def test_success_no_likes(self, mock_requests, mock_api_keys):
        from plugins import youtube

        data = deepcopy(video_data)
        del data["items"][0]["statistics"]["likeCount"]

        mock_requests.add(
            "GET",
            self.api_url.format(id="phL7P6gtZRM", key="APIKEY"),
            match_querystring=True,
            json=data,
        )

        result = (
            "\x02some title\x02 - length \x0217m 2s\x02 - \x0268,905\x02 views - "
            "\x02a channel\x02 on \x022019.10.10\x02"
        )

        assert youtube.get_video_description("phL7P6gtZRM") == result

    def test_success_nsfw(self, mock_requests, mock_api_keys):
        from plugins import youtube

        data = deepcopy(video_data)
        data["items"][0]["contentDetails"]["contentRating"] = "18+"

        mock_requests.add(
            "GET",
            self.api_url.format(id="phL7P6gtZRM", key="APIKEY"),
            match_querystring=True,
            json=data,
        )

        result = (
            "\x02some title\x02 - length \x0217m 2s\x02 - "
            "4,633 likes, 31 dislikes (\x0299.3\x02%) - "
            "\x0268,905\x02 views - \x02a channel\x02 on \x022019.10.10\x02 - "
            "\x034NSFW\x02"
        )

        assert youtube.get_video_description("phL7P6gtZRM") == result

    def test_no_results(self, mock_requests, mock_api_keys):
        from plugins import youtube

        data = deepcopy(video_data)
        del data["items"][0]

        mock_requests.add(
            "GET",
            self.api_url.format(id="phL7P6gtZRM", key="APIKEY"),
            match_querystring=True,
            json=data,
        )

        assert youtube.get_video_description("phL7P6gtZRM") is None

    def test_command_error_reply(self, mock_requests, mock_api_keys):
        from plugins import youtube

        mock_requests.add(
            "GET",
            "https://www.googleapis.com/youtube/v3/search",
            json={
                "items": [{"id": {"videoId": "foobar"}}],
                "pageInfo": {"totalResults": 1},
            },
        )

        mock_requests.add(
            "GET",
            self.api_url.format(id="foobar", key="APIKEY"),
            match_querystring=True,
            json={"error": {"code": 500}},
            status=500,
        )

        reply = MagicMock()

        with pytest.raises(youtube.APIError):
            youtube.youtube("test video", reply)

        reply.assert_called_with("Unknown error")
