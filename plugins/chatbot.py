from cleverwrap import CleverWrap

from cloudbot import hook
from cloudbot.bot import bot

api = CleverWrap(bot.config.get_api_key("cleverbot"))


@hook.command("ask", "gonzo", "gonzobot", "cleverbot", "cb")
def chitchat(text):
    """<text> - chat with cleverbot.com"""
    if not api:
        return "Please add an API key from http://www.cleverbot.com/api to enable this feature."

    return api.say(text)
