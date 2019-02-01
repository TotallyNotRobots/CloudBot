from cleverwrap import CleverWrap

from cloudbot import hook

api = None


@hook.on_start()
def get_key(bot):
    global api
    api_key = bot.config.get("api_keys", {}).get("cleverbot", None)
    if api_key:
        api = CleverWrap(api_key)


@hook.command("ask", "gonzo", "gonzobot", "cleverbot", "cb")
def chitchat(text):
    """<text> - chat with cleverbot.com"""
    if not api:
        return "Please add an API key from http://www.cleverbot.com/api to enable this feature."

    return api.say(text)
