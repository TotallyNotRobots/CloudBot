import pytest

from plugins import googleurlparse


@pytest.mark.parametrize(
    "text,url",
    [
        ("www.google.com/url?thing&url=example.com", "example.com"),
    ],
)
def test_google_url(text, url):
    match = googleurlparse.spamurl.search(text)
    assert match
    assert googleurlparse.google_url(match) == url
