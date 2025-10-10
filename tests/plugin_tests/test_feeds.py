from feedparser import FeedParserDict

from plugins import feeds


def test_feeds(mock_feedparse, patch_try_shorten):
    mock_feedparse.return_value = FeedParserDict(
        entries=[],
    )
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


def test_feeds_block_file(mock_feedparse, patch_try_shorten):
    assert feeds.rss("file://etc/passwd") == "Invalid URL scheme."
    assert feeds.rss("ftp://example.com/feed.xml") == "Invalid URL scheme."
    assert feeds.rss("javascript:alert(1)") == "Invalid URL scheme."
    assert feeds.rss("data:text/plain,HelloWorld") == "Invalid URL scheme."
    assert feeds.rss("/dev/null") == "Invalid URL scheme."
    assert feeds.rss("C:\\Windows\\System32") == "Invalid URL scheme."
    assert feeds.rss("not a url") == "Invalid URL."
    mock_feedparse.assert_not_called()
