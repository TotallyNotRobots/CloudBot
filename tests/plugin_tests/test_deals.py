import pytest
from feedparser import FeedParserDict

from plugins import deals


@pytest.mark.usefixtures("patch_try_shorten")
def test_slickdeals(mock_feedparse) -> None:
    feed = FeedParserDict(entries=[FeedParserDict(link="foo", title="bar")])
    mock_feedparse.return_value = feed

    out = deals.slickdeals()
    assert out == "slickdeals.net: bar (foo)"
