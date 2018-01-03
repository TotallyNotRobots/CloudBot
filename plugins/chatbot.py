from cleverwrap import CleverWrap

from cloudbot import hook


@hook.on_start()
def get_key(bot):
    global api_key, cb
    api_key = bot.config.get("api_keys", {}).get("cleverbot", None)
    cb = CleverWrap(api_key)


@hook.command("ask", "gonzo", "gonzobot", "cleverbot", "cb")
def chitchat(text):
    """<text> - chat with cleverbot.com"""
    if not api_key:
        return "Please add an API key from http://www.cleverbot.com/api to enable this feature."
    return cb.say(text)
