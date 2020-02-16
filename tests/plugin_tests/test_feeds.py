from unittest.mock import patch

import pytest
from feedparser import FeedParserDict


@pytest.fixture()
def mock_feedparse():
    with patch("feedparser.parse") as mock:
        yield mock


def test_feeds(mock_feedparse, patch_try_shorten):
    from plugins import feeds

    mock_feedparse.return_value = FeedParserDict(entries=[],)
    assert feeds.rss("xkcd") == "Feed not found."

    mock_feedparse.assert_called_with("http://xkcd.com/rss.xml")

    mock_feedparse.reset_mock()

    mock_feedparse.return_value = FeedParserDict(
        entries=[FeedParserDict(title="foo1", link="http://example.com")],
        feed=FeedParserDict(title="test"),
    )

    with_title = "\x02test\x02: foo1 (http://example.com)"

    assert feeds.rss("http://rss.example.com/feed.xml") == with_title

    mock_feedparse.assert_called_with("http://rss.example.com/feed.xml")

    mock_feedparse.reset_mock()

    mock_feedparse.return_value = FeedParserDict(
        entries=[FeedParserDict(title="foo1", link="http://example.com")],
        feed=FeedParserDict(),
    )

    without_title = "foo1 (http://example.com)"

    assert feeds.rss("http://rss.example.com/feed.xml") == without_title

    mock_feedparse.assert_called_with("http://rss.example.com/feed.xml")

    mock_feedparse.reset_mock()
