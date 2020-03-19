from unittest.mock import MagicMock

import pytest
import tweepy
from responses import RequestsMock

from cloudbot.config import Config


@pytest.fixture()
def mock_requests():
    with RequestsMock() as reqs:
        yield reqs


class MockConfig(Config):
    def load_config(self):
        self._api_keys.clear()

    def get_api_key(self, name, default=None):
        return "API_KEY"


def test_twitter_url(mock_requests, unset_bot):
    from cloudbot.bot import bot
    bot.set(MagicMock())

    mock_conn = MagicMock()
    mock_conn.config = {}
    mock_conn.bot = bot.get()
    bot.get().config = MockConfig(bot.get())

    from plugins import twitter

    result = twitter.twitter_url(
        twitter.TWITTER_RE.search('twitter.com/FakeUser/status/11235'),
        mock_conn,
    )

    assert result is None

    twitter.set_api()

    with pytest.raises(tweepy.TweepError):
        twitter.twitter_url(
            twitter.TWITTER_RE.search('twitter.com/FakeUser/status/11235'),
            mock_conn,
        )

    mock_requests.add(
        'GET',
        'https://api.twitter.com/1.1/statuses/show.json'
        '?id=11235&tweet_mode=extended',
        json={
            "errors": [{
                "message": "No status found with that ID.",
                "code": 144,
            }],
        },
        status=404,
    )

    result = twitter.twitter_url(
        twitter.TWITTER_RE.search('twitter.com/FakeUser/status/11235'),
        mock_conn,
    )

    assert result is None
