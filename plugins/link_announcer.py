import re

import requests

from cloudbot import hook
from cloudbot.hook import Action, Priority
from cloudbot.util.http import parse_soup

MAX_TITLE = 100

ENCODED_CHAR = r"%[A-F0-9]{2}"
PATH_SEG_CHARS = r"[A-Za-z0-9!$&'*-.:;=@_~\u00A0-\U0010FFFD]|" + ENCODED_CHAR
QUERY_CHARS = PATH_SEG_CHARS + r"|/"
FRAG_CHARS = QUERY_CHARS


def no_parens(pattern):
    return r"{0}|\(({0}|[\(\)])*\)".format(pattern)


# This will match any URL, blacklist removed and abstracted to a priority/halting system
url_re = re.compile(
    r"""
    https? # Scheme
    ://

    # Username and Password
    (?:
        (?:[^\[\]?/<~#`!@$%^&*()=+}|:";',>{\s]|%[0-9A-F]{2})*
        (?::(?:[^\[\]?/<~#`!@$%^&*()=+}|:";',>{\s]|%[0-9A-F]{2})*)?
        @
    )?

    # Domain
    (?:
        # TODO Add support for IDNA hostnames as specified by RFC5891
        (?:
            [\-.0-9A-Za-z]+|  # host
            \d{1,3}(?:\.\d{1,3}){3}|  # IPv4
            \[[A-F0-9]{0,4}(?::[A-F0-9]{0,4}){2,7}\]  # IPv6
        )
        (?<![.,?!\]])  # Invalid end chars
    )

    (?::\d*)?  # port

    (?:/(?:"""
    + no_parens(PATH_SEG_CHARS)
    + r""")*(?<![.,?!\]]))*  # Path segment

    (?:\?(?:"""
    + no_parens(QUERY_CHARS)
    + r""")*(?<![.,!\]]))?  # Query

    (?:\#(?:"""
    + no_parens(FRAG_CHARS)
    + r""")*(?<![.,?!\]]))?  # Fragment
    """,
    re.IGNORECASE | re.VERBOSE,
)

HEADERS = {
    "Accept-Language": "en-US,en;q=0.5",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/53.0.2785.116 Safari/537.36",
}

MAX_RECV = 1000000


def get_encoding(soup):
    meta_charset = soup.find("meta", charset=True)

    if meta_charset:
        return meta_charset["charset"]

    meta_content_type = soup.find(
        "meta",
        {
            "http-equiv": lambda t: t and t.lower() == "content-type",
            "content": True,
        },
    )
    if meta_content_type:
        return requests.utils.get_encoding_from_headers(
            {"content-type": meta_content_type["content"]}
        )

    return None


def parse_content(content, encoding=None):
    html = parse_soup(content, from_encoding=encoding)
    old_encoding = encoding

    encoding = get_encoding(html)

    if encoding is not None and encoding != old_encoding:
        html = parse_soup(content, from_encoding=encoding)

    return html


@hook.regex(
    url_re, priority=Priority.LOW, action=Action.HALTTYPE, only_no_match=True
)
def print_url_title(message, match, logger):
    try:
        with requests.get(
            match.group(), headers=HEADERS, stream=True, timeout=3
        ) as r:
            if not r.encoding or not r.ok:
                return

            content = r.raw.read(MAX_RECV, decode_content=True)
            encoding = r.encoding
    except requests.exceptions.ReadTimeout:
        logger.debug("Read timeout reached for %r", match.group())
        return
    except requests.ConnectionError:
        logger.warning("Connection error in link_announcer.py", exc_info=1)
        return

    html = parse_content(content, encoding)

    if html.title and html.title.text:
        title = html.title.text.strip()

        if len(title) > MAX_TITLE:
            title = title[:MAX_TITLE] + " ... [trunc]"

        out = "Title: \x02{}\x02".format(title)
        message(out)
