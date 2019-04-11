import traceback

from requests.exceptions import RequestException

from cloudbot import hook
from cloudbot.util import web


def get_attrs(obj):
    try:
        return list(obj.__dict__.keys())
    except AttributeError:
        return dir(obj)


def dump_attrs(obj):
    for name in get_attrs(obj):
        yield (name, getattr(obj, name, None))


def format_error_data(exc):
    while exc:
        yield repr(exc)
        for name, val in dump_attrs(exc):
            if len(name) > 4 and name.startswith('__') and name.endswith('__'):
                # Ignore dunder fields
                continue

            yield '  {} = {!r}'.format(name, val)

        yield ''
        # Get "direct cause of" or
        # "during handling of ..., another exception occurred" stack
        cause = getattr(exc, '__cause__', None)
        context = getattr(exc, '__context__', None)
        exc = cause or context


def _format_attrs(obj):
    for k, v in dump_attrs(obj):
        yield '{} = {!r}'.format(k, v)


@hook.post_hook
def on_hook_end(error, launched_hook, launched_event, admin_log):
    if error is None:
        return

    should_broadcast = True
    messages = [
        "Error occurred in {}.{}".format(
            launched_hook.plugin.title, launched_hook.function_name
        )
    ]

    try:
        lines = traceback.format_exception(*error)
        last_line = lines[-1]
        messages.append(last_line.strip())
    except Exception:
        msg = traceback.format_exc()[-1]
        messages.append(
            "Error occurred while formatting error {}".format(msg)
        )
    else:
        try:
            url = web.paste('\n'.join(lines))
            messages.append("Traceback: " + url)
        except Exception:
            msg = traceback.format_exc()[-1]
            messages.append(
                "Error occurred while gathering traceback {}".format(msg)
            )

    try:
        lines = list(_format_attrs(launched_event))
        _, exc, _ = error

        lines.append("")
        lines.append("Error data:")
        lines.extend(format_error_data(exc))

        if isinstance(exc, RequestException):
            if exc.request is not None:
                req = exc.request
                lines.append("")
                lines.append("Request Info:")
                lines.extend(_format_attrs(req))

            if exc.response is not None:
                response = exc.response
                lines.append("")
                lines.append("Response Info:")
                lines.extend(_format_attrs(response))

        url = web.paste('\n'.join(lines))
        messages.append("Event: " + url)
    except Exception:
        msg = traceback.format_exc()[-1]
        messages.append(
            "Error occurred while gathering error data {}".format(msg)
        )

    for message in messages:
        admin_log(message, should_broadcast)
