import traceback

from cloudbot import hook
from cloudbot.util import web


@hook.post_hook
def on_hook_end(error, launched_hook, launched_event, conn, admin_log):
    should_broadcast = conn is None
    if error is not None:
        admin_log(
            "Error occurred in {}.{}".format(launched_hook.plugin.title, launched_hook.function_name), should_broadcast
        )

        lines = traceback.format_exception(*error)
        last_line = lines[-1]
        admin_log(last_line, should_broadcast)
        url = web.paste('\n'.join(lines))
        admin_log("Traceback: " + url, should_broadcast)

        event_data = launched_event.__dict__.items()
        lines = ["{} = {}".format(k, v) for k, v in event_data]
        url = web.paste('\n'.join(lines))
        admin_log("Event: " + url, should_broadcast)
