from plugins.link_announcer import url_re

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
    ("<a hreh=\"https://example.com/test.page?#test\">", "https://example.com/test.page?#test"),
    ("<https://www.example.com/this.is.a.test/blah.txt?a=1#123>", "https://www.example.com/this.is.a.test/blah.txt?a=1#123"),
)


def test_urls():
    for url in MATCHES:
        assert url_re.fullmatch(url), url

    for url in FAILS:
        match = url_re.fullmatch(url)
        assert not match, match.group()


def test_search():
    for text, out in SEARCH:
        match = url_re.search(text)
        assert match and match.group() == out
