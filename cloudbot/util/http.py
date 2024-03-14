# convenience wrapper for urllib2 & friends

import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request
import warnings
from typing import Dict, Union
from urllib.parse import quote_plus as _quote_plus

from bs4 import BeautifulSoup
from lxml import etree, html
from multidict import MultiDict
from yarl import URL

# security
parser = etree.XMLParser(resolve_entities=False, no_network=True)

ua_cloudbot = "Cloudbot/DEV https://github.com/CloudDev/CloudBot"

ua_firefox = (
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:17.0) Gecko/17.0 Firefox/17.0"
)
ua_old_firefox = (
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; "
    "rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6"
)
ua_internetexplorer = "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)"
ua_chrome = (
    "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.4 (KHTML, "
    "like Gecko) Chrome/22.0.1229.79 Safari/537.4"
)

jar = http.cookiejar.CookieJar()


def get(*args, **kwargs):
    if kwargs.get("decode", True):
        return open_request(*args, **kwargs).read().decode()

    return open_request(*args, **kwargs).read()


def get_url(*args, **kwargs):
    return open_request(*args, **kwargs).geturl()


def get_html(*args, **kwargs):
    return html.fromstring(get(*args, **kwargs))


def parse_soup(text, features=None, **kwargs):
    """
    Parse HTML using BeautifulSoup

    >>> p = parse_soup('<p><h1>test</h1></p>')
    >>> p.h1.text
    'test'
    """
    if features is None:
        features = "lxml"

    return BeautifulSoup(text, features=features, **kwargs)


def get_soup(*args, **kwargs):
    return parse_soup(get(*args, **kwargs))


def get_xml(*args, **kwargs):
    kwargs["decode"] = False  # we don't want to decode, for etree
    return parse_xml(get(*args, **kwargs))


def parse_xml(text):
    """
    >>> elem = parse_xml('<foo>bar</foo>')
    >>> elem.tag
    'foo'
    >>> elem.text
    'bar'
    """
    return etree.fromstring(text, parser=parser)  # nosec


def get_json(*args, **kwargs):
    return json.loads(get(*args, **kwargs))


def open_request(
    url,
    query_params=None,
    user_agent=None,
    post_data=None,
    referer=None,
    get_method=None,
    cookies=False,
    timeout=None,
    headers=None,
    **kwargs,
):
    if query_params is None:
        query_params = {}

    if user_agent is None:
        user_agent = ua_cloudbot

    query_params.update(kwargs)

    url = prepare_url(url, query_params)

    request = urllib.request.Request(url, post_data, method=get_method)

    if headers is not None:
        for header_key, header_value in headers.items():
            request.add_header(header_key, header_value)

    request.add_header("User-Agent", user_agent)

    if referer is not None:
        request.add_header("Referer", referer)

    if cookies:
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar)
        )
    else:
        opener = urllib.request.build_opener()

    if timeout:
        return opener.open(request, timeout=timeout)

    return opener.open(request)


# noinspection PyShadowingBuiltins
def open(
    url,
    query_params=None,
    user_agent=None,
    post_data=None,
    referer=None,
    get_method=None,
    cookies=False,
    timeout=None,
    headers=None,
    **kwargs,
):  # pylint: disable=locally-disabled, redefined-builtin  # pragma: no cover
    warnings.warn(
        "http.open() is deprecated, use http.open_request() instead.",
        DeprecationWarning,
    )

    return open_request(
        url,
        query_params=query_params,
        user_agent=user_agent,
        post_data=post_data,
        referer=referer,
        get_method=get_method,
        cookies=cookies,
        timeout=timeout,
        headers=headers,
        **kwargs,
    )


def prepare_url(url, queries):
    """
    >>> str(unify_url(prepare_url("https://example.com?foo=bar", {'a': 1, 'b': 2})))
    'https://example.com/?a=1&b=2&foo=bar'
    """
    if queries:
        scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)

        query = dict(urllib.parse.parse_qsl(query))
        query.update(queries)
        query = urllib.parse.urlencode(
            dict((to_utf8(key), to_utf8(value)) for key, value in query.items())
        )

        url = urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))

    return url


def to_utf8(s):
    """
    >>> to_utf8('foo bar')
    b'foo bar'
    >>> to_utf8(b'foo bar')
    b'foo bar'
    >>> to_utf8(1)
    b'1'
    """
    if isinstance(s, str):
        return s.encode("utf8", "ignore")

    if isinstance(s, bytes):
        return bytes(s)

    return to_utf8(str(s))


def quote_plus(s):
    """
    >>> quote_plus(b'foo bar')
    'foo+bar'
    """
    return _quote_plus(to_utf8(s))


def unescape(s):
    """
    >>> unescape('')
    ''
    >>> unescape(' ')
    ' '
    >>> unescape('<p>&lt;</p>')
    '<'
    """
    if not s.strip():
        return s
    return html.fromstring(s).text_content()


UrlOrStr = Union[str, URL]


def unify_url(url: UrlOrStr) -> URL:
    parsed = URL(url)
    return parsed.with_query(MultiDict(sorted(parsed.query.items())))


def compare_urls(a: UrlOrStr, b: UrlOrStr) -> bool:
    """Compare two URLs, unifying them first"""
    return unify_url(a) == unify_url(b)


GetParams = Dict[str, Union[str, int]]
