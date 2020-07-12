import re
from urllib.parse import unquote

from cloudbot import hook

spamurl = re.compile(r".*(((www\.)?google\.com/url\?)[^ ]+)", re.I)


@hook.regex(spamurl)
def google_url(match):
    matches = match.group(1)
    url = matches

    url = "http://{}".format(url)
    parts = [
        (unquote(a[4:]) if a[:4] == "url=" else "") for a in url.split("&")
    ]
    out = "".join(parts).replace(", ,", "").strip()
    return out
