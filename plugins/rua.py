import requests

from cloudbot import hook
from cloudbot.util.http import parse_soup


@hook.command("ruad", "rud", "ruadick")
def RUADICK(text, message):
    """<username> - checks ruadick.com to see if you're a dick on reddit"""
    DickCheck = text.strip()
    dickstatus = requests.get("http://www.ruadick.com/user/{}".format(DickCheck))
    dickstatus.raise_for_status()
    DickSoup = parse_soup(dickstatus.content)
    Dickstr = str(DickSoup.h2)

    dickstrip = Dickstr.lstrip("<h2>").rstrip("</h2>")

    if dickstrip == "None":
        message("I can't find that user")
    else:
        message("{} {}".format(dickstrip, dickstatus.url))
