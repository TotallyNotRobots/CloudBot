# Author: Matheus Fillipe
# Date: 30/04/2023
# Description: Display our radio url

from cloudbot import hook
from cloudbot.util import formatting


@hook.command("radio", autohelp=False)
def radio(text, bot):
    """Display radio url"""
    return "https://radio.dot.org.es/stream.ogg"
