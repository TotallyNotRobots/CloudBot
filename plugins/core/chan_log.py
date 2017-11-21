import traceback

from cloudbot import hook
from cloudbot.util import web

logchannel = ""


@hook.post_hook
def on_hook_end(error, message, launched_hook, launched_event):
    if error is not None and logchannel:
        message("Error occurred in {}.{}".format(launched_hook.plugin.title, launched_hook.function_name), logchannel)

        lines = traceback.format_exception(*error)
        last_line = lines[-1]
        message(last_line, logchannel)
        url = web.paste('\n'.join(lines))
        message("Traceback: " + url, logchannel)

        event_data = launched_event.__dict__.items()
        lines = ["{} = {}".format(k, v) for k, v in event_data]
        url = web.paste('\n'.join(lines))
        message("Event: " + url, logchannel)
