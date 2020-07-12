from cleverwrap import CleverWrap

from cloudbot import hook

no_key = (
    "Please add an API key from http://www.cleverbot.com/api to "
    "enable this feature."
)


class APIContainer:
    api = None


container = APIContainer()


@hook.on_start
def make_api(bot):
    container.api = CleverWrap(bot.config.get_api_key("cleverbot"))


@hook.command("ask", "gonzo", "gonzobot", "cleverbot", "cb")
def chitchat(text):
    """<text> - chat with cleverbot.com"""
    if not container.api:
        return no_key

    return container.api.say(text)
