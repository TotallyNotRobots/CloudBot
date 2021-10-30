import codecs
from unittest.mock import MagicMock

import pytest
import requests
from bs4 import BeautifulSoup

from plugins import link_announcer

MATCHES = (
    "http://foo.com/blah_blah",
    "http://foo.com/blah_blah/",
    "http://foo.com/blah_blah_(wikipedia)",
    "http://foo.com/blah_blah_(wikipedia)_(again)",
    "http://www.example.com/wpstyle/?p=364",
    "https://www.example.com/foo/?bar=baz&inga=42&quux",
    "http://userid:password@example.com:8080",
    "http://userid:password@example.com:8080/",
    "http://userid@example.com",
    "http://userid@example.com/",
    "http://userid@example.com:8080",
    "http://userid@example.com:8080/",
    "http://userid:password@example.com",
    "http://userid:password@example.com/",
    "http://142.42.1.1/",
    "http://142.42.1.1:8080/",
    "http://foo.com/blah_(wikipedia)#cite-1",
    "http://foo.com/blah_(wikipedia)_blah#cite-1",
    "http://foo.com/unicode_(✪)_in_parens",
    "http://foo.com/(something)?after=parens",
    "http://code.google.com/events/#&product=browser",
    "http://j.mp",
    "http://foo.bar/?q=Test%20URL-encoded%20stuff",
    "http://1337.net",
    "http://a.b-c.de",
    "http://223.255.255.254",
    "https://foo.bar/baz?#",
    "https://foo.bar/baz?",
)

FAILS = (
    "http://",
    "http://.",
    "http://..",
    "http://?",
    "http://??",
    "http://??/",
    "http://#",
    "http://##",
    "http://##/",
    "http://foo.bar?q=Spaces should be encoded",
    "//",
    "//a",
    "///a",
    "///",
    "http:///a",
    "foo.com",
    "rdar://1234",
    "h://test",
    "http:// shouldfail.com",
    ":// should fail",
    "http://foo.bar/foo(bar)baz quux",
    "ftps://foo.bar/",
    "https://foo.bar/baz.ext)",
    "https://foo.bar/test.",
    "https://foo.bar/test(test",
    "https://foo.bar.",
    "https://foo.bar./",
)

SEARCH = (
    ("(https://foo.bar)", "https://foo.bar"),
    ("[https://example.com]", "https://example.com"),
    (
        '<a hreh="https://example.com/test.page?#test">',
        "https://example.com/test.page?#test",
    ),
    (
        "<https://www.example.com/this.is.a.test/blah.txt?a=1#123>",
        "https://www.example.com/this.is.a.test/blah.txt?a=1#123",
    ),
)


def test_urls():
    for url in MATCHES:
        assert link_announcer.url_re.fullmatch(url), url

    for url in FAILS:
        match = link_announcer.url_re.fullmatch(url)
        assert not match, match.group()


def test_search():
    for text, out in SEARCH:
        match = link_announcer.url_re.search(text)
        assert match and match.group() == out


ENCODINGS = (
    (b'<meta charset="utf8">', codecs.lookup("utf8")),
    (b"", None),
    (
        b'<meta http-equiv="Content-Type" content="text/html; charset=utf-8">',
        codecs.lookup("utf8"),
    ),
)


def test_encoding_parse():
    for text, enc in ENCODINGS:
        soup = BeautifulSoup(text, "lxml")
        encoding = link_announcer.get_encoding(soup)
        if encoding is None:
            assert (
                enc is None
            ), "Got empty encoding from {!r} expected {!r}".format(text, enc)
            continue

        enc_obj = codecs.lookup(encoding)

        assert enc, enc_obj


STD_HTML = "<head><title>{}</title></head>"
TESTS = {
    "http://www.montypython.fun": (
        "<!DOCTYPE html><head><title>{}</title></head><body>test</body>",
        "This Site is dead.",
    ),
    "http://www.talos.principle": (STD_HTML, "In the beginning were the words"),
    "http://www.nonexistent.lol": ("", False),
    "http://www.much-newlines.backslashn": (
        ("\n" * 500) + STD_HTML,
        "new lines!",
    ),
    "http://completely.invalid": ("\x01\x01\x02\x03\x05\x08\x13", False),
    "http://large.amounts.of.text": (
        STD_HTML + ("42" * 512 * 4096) + "</body>",
        "here have a couple megs of text",
    ),
    "http://star.trek.the.next.title": (STD_HTML, "47" * 512 * 4096),
    "http://bare.title": ("<title>{}</title>", "here has title"),
}


@pytest.mark.parametrize(
    "match,test_str,res",
    [
        (link_announcer.url_re.search(a), b.format(c), c)
        for a, (b, c) in TESTS.items()
    ],
    ids=lambda case: str(getattr(case, "string", case))[:100],
)
def test_link_announce(match, test_str, res, mock_requests):
    mock_requests.add("GET", match.string, body=test_str)
    mck = MagicMock()
    logger = MagicMock()

    link_announcer.print_url_title(match=match, message=mck, logger=logger)
    if res:
        if len(res) > link_announcer.MAX_TITLE:
            res = res[: link_announcer.MAX_TITLE] + " ... [trunc]"

        mck.assert_called_with("Title: \x02" + res + "\x02")
    else:
        mck.assert_not_called()


def test_link_announce_404(mock_requests):
    url = "http://example.com"
    mock_requests.add("GET", url, status=404)

    match = link_announcer.url_re.search(url)
    assert match
    mck = MagicMock()
    logger = MagicMock()

    assert (
        link_announcer.print_url_title(match=match, message=mck, logger=logger)
        is None
    )

    mck.assert_not_called()


def test_read_timeout(mock_requests):
    url = "http://example.com"

    def callback(resp):
        raise requests.ReadTimeout()

    mock_requests.add_callback("GET", url, callback)

    match = link_announcer.url_re.search(url)
    assert match
    mck = MagicMock()
    logger = MagicMock()

    assert (
        link_announcer.print_url_title(match=match, message=mck, logger=logger)
        is None
    )

    logger.debug.assert_called_with("Read timeout reached for %r", url)


@pytest.mark.parametrize(
    "body,encoding",
    [
        (
            b"""\
<head>
<meta charset="utf8">
<title>foobar</title>
</head>""",
            "utf8",
        ),
        (
            b"""\
<head>
<meta http-equiv="content-type", content="text/plain; charset=utf8">
<title>foobar</title>
</head>""",
            "utf8",
        ),
        (
            b"""\
<head>
<meta http-equiv="content-type", content="text/plain">
<title>foobar</title>
</head>""",
            "ISO-8859-1",
        ),
        (
            b"""\
<head>
<title>foobar</title>
</head>""",
            "ISO-8859-1",
        ),
    ],
)
def test_change_encoding(body, encoding):
    # ISO-8859-1 is the default encoding requests would return if none is found
    assert (
        link_announcer.parse_content(body, "ISO-8859-1").original_encoding
        == encoding
    )


def test_connection_error(mock_requests):
    url = "http://example.com"

    match = link_announcer.url_re.search(url)
    assert match
    mck = MagicMock()
    logger = MagicMock()

    assert (
        link_announcer.print_url_title(match=match, message=mck, logger=logger)
        is None
    )

    assert logger.warning.called
