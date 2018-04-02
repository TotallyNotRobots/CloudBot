import re
from contextlib import closing

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

MAX_RECV = 1000000


@hook.regex(url_re, priority=Priority.LOW, action=Action.HALTTYPE, only_no_match=True)
def print_url_title(message, match):
    with closing(requests.get(match.group(), headers=HEADERS, stream=True, timeout=3)) as r:
        r.raise_for_status()
        if not r.encoding:
            return

        content = r.raw.read(MAX_RECV + 1, decode_content=True)
        encoding = r.encoding

    if len(content) > MAX_RECV:
        return

    html = BeautifulSoup(content, "lxml", from_encoding=encoding)

    if html.title:
        title = html.title.text
        out = "Title: \x02{}\x02".format(title.strip())
        message(out)
