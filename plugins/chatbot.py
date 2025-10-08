from cleverwrap import CleverWrap

from cloudbot import hook


class APIContainer:
    api: CleverWrap | None = None


container = APIContainer()


@hook.on_start()
def make_api(bot):
    container.api = CleverWrap(bot.config.get_api_key("cleverbot"))


@hook.command("ask", "gonzo", "gonzobot", "cleverbot", "cb")
def chitchat(text):
    """<text> - chat with cleverbot.com"""
    if not container.api:
        return "Please add an API key from http://www.cleverbot.com/api to enable this feature."

    return container.api.say(text)
