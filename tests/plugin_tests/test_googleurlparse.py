import pytest


@pytest.mark.parametrize(
    "text,url",
    [
        ("www.google.com/url?thing&url=example.com", "example.com"),
    ],
)
def test_google_url(text, url):
    from plugins.googleurlparse import google_url, spamurl

    match = spamurl.search(text)
    assert match
    assert google_url(match) == url
