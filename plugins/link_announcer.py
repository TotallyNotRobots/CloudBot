import re

import requests
from bs4 import BeautifulSoup

from cloudbot import hook
from cloudbot.hooks.actions import Action
from cloudbot.hooks.priority import Priority

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
    
    (?:/(?:""" + no_parens(PATH_SEG_CHARS) + r""")*(?<![.,?!\]]))*  # Path segment
    
    (?:\?(?:""" + no_parens(QUERY_CHARS) + r""")*(?<![.,!\]]))?  # Query
    
    (?:\#(?:""" + no_parens(FRAG_CHARS) + r""")*(?<![.,?!\]]))?  # Fragment
    """,
    re.IGNORECASE | re.VERBOSE
)

HEADERS = {
    'Accept-Language': 'en-US,en;q=0.5',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36'
}

CHUNK_SIZE = 512
MAX_CHUNKS = 4096
MAX_RECV = CHUNK_SIZE * MAX_CHUNKS


def get_encoding(soup):
    meta_charset = soup.find('meta', charset=True)

    if meta_charset:
        return meta_charset['charset']
    else:
        meta_content_type = soup.find(
            'meta', {'http-equiv': lambda t: t and t.lower() == 'content-type', 'content': True}
        )
        if meta_content_type:
            return requests.utils.get_encoding_from_headers({'content-type': meta_content_type['content']})

    return None


def parse_content(content, encoding=None):
    html = BeautifulSoup(content, "lxml", from_encoding=encoding)
    old_encoding = encoding

    encoding = get_encoding(html)

    if encoding is not None and encoding != old_encoding:
        html = BeautifulSoup(content, "lxml", from_encoding=encoding)

    return html


find_title = re.compile(
    br'<title.*?>.*?</title>', re.IGNORECASE | re.MULTILINE | re.DOTALL
).search


@hook.regex(url_re, priority=Priority.LOW, action=Action.HALTTYPE, only_no_match=True)
def print_url_title(match):
    content = b""
    with requests.get(match.group(), headers=HEADERS, stream=True) as response:
        response.raise_for_status()
        for chunk in response.iter_content(CHUNK_SIZE):
            content += chunk
            if find_title(content) or len(content) > MAX_RECV:
                break

        encoding = response.encoding
        if encoding is None:
            encoding = response.apparent_encoding

    html = parse_content(content, encoding)
    title = html.title
    if title and title.text and title.text.strip():
        return "Title: \x02{}\x02".format(title.text.strip())
