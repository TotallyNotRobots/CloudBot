import re
from contextlib import closing

import requests
from bs4 import BeautifulSoup

from cloudbot import hook
from cloudbot.hook import Priority, Action

# This will match any URL, blacklist removed and abstracted to a priority/halting system
url_re = re.compile(r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+~]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', re.I)

opt_out = []

HEADERS = {
    'Accept-Language': 'en-US,en;q=0.5',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36'
}

MAX_RECV = 1000000


@hook.regex(url_re, priority=Priority.LOW, action=Action.HALTTYPE, only_no_match=True)
def print_url_title(message, match, chan):
    if chan in opt_out:
        return

    with closing(requests.get(match.group(), headers=HEADERS, stream=True, timeout=3)) as r:
        r.raise_for_status()
        if not r.encoding:
            return

        content = r.raw.read(MAX_RECV + 1, decode_content=True)
        encoding = r.encoding

    if len(content) > MAX_RECV:
        return

    html = BeautifulSoup(content, "lxml", from_encoding=encoding)
    title = " ".join(html.title.text.strip().splitlines())
    out = "Title: \x02{}\x02".format(title)
    message(out, chan)
