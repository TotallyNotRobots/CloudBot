import pytest


@pytest.mark.parametrize(
    "text,url", [("www.google.com/url?thing&url=example.com", "example.com"),]
)
def test_google_url(text, url):
    from plugins.googleurlparse import spamurl, google_url

    match = spamurl.search(text)
    assert match
    assert google_url(match) == url
