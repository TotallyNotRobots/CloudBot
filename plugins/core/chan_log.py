import traceback

from requests.exceptions import RequestException

from cloudbot import hook
from cloudbot.util import web


def _dump_attrs(obj):
    for name in dir(obj):
        if not name.startswith('_'):
            yield name, getattr(obj, name, None)


@hook.post_hook
def on_hook_end(error, launched_hook, launched_event, admin_log):
    should_broadcast = True
    if error is not None:
        admin_log(
            "Error occurred in {}.{}".format(launched_hook.plugin.title, launched_hook.function_name), should_broadcast
        )

        lines = traceback.format_exception(*error)
        last_line = lines[-1]
        admin_log(last_line, should_broadcast)
        url = web.paste('\n'.join(lines))
        admin_log("Traceback: " + url, should_broadcast)

        lines = ["{} = {}".format(k, v) for k, v in _dump_attrs(launched_event)]
        exc_type, exc, exc_tb = error

        lines.append("")
        lines.append("Error data:")
        lines.extend("{} = {}".format(k, v) for k, v in _dump_attrs(exc))

        if isinstance(exc, RequestException):
            if exc.request is not None:
                req = exc.request
                lines.append("")
                lines.append("Request Info:")
                lines.extend("{} = {}".format(k, v) for k, v in _dump_attrs(req))

            if exc.response is not None:
                response = exc.response
                lines.append("")
                lines.append("Response Info:")
                lines.extend("{} = {}".format(k, v) for k, v in _dump_attrs(response))

        url = web.paste('\n'.join(lines))
        admin_log("Event: " + url, should_broadcast)
