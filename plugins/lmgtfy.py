from urllib.parse import quote

from cloudbot import hook
from cloudbot.util import web


@hook.command("lmgtfy", "gfy")
def lmgtfy(text):
    """[phrase] - gets a lmgtfy.com link for the specified phrase"""

    link = f"http://lmgtfy.com/?q={quote(text)}"

    return web.try_shorten(link)
