from feedparser import FeedParserDict

from plugins import deals


def test_slickdeals(patch_try_shorten, mock_feedparse):
    feed = FeedParserDict(entries=[FeedParserDict(link="foo", title="bar")])
    mock_feedparse.return_value = feed

    out = deals.slickdeals()
    assert out == "slickdeals.net: bar (foo)"
