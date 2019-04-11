import traceback

from requests.exceptions import RequestException

from cloudbot import hook
from cloudbot.util import web


def get_attrs(obj):
    try:
        return list(obj.__dict__.keys())
    except AttributeError:
        return dir(obj)


def is_dunder(name):
    return len(name) > 4 and name.startswith('__') and name.endswith('__')


def dump_attrs(obj, ignore_dunder=False):
    for name in get_attrs(obj):
        if ignore_dunder and is_dunder(name):
            # Ignore dunder fields
            continue

        yield (name, getattr(obj, name, None))


def indent(lines, size=2, char=' '):
    for line in lines:
        if line:
            yield (char * size) + line
        else:
            yield line


def format_requests_exc(exc: RequestException):
    def _format(title, obj):
        if obj is not None:
            yield title
            yield from indent(format_attrs(obj))

    yield from _format("Request Info", exc.request)
    yield from _format("Response Info", exc.response)


SPECIAL_CASES = {
    RequestException: format_requests_exc,
}


def format_error_data(exc):
    yield repr(exc)
    yield from indent(format_attrs(exc, ignore_dunder=True))

    for typ, func in SPECIAL_CASES.items():
        if isinstance(exc, typ):
            yield from indent(func(exc))

    yield ''


def format_error_chain(exc):
    while exc:
        yield from format_error_data(exc)
        # Get "direct cause of" or
        # "during handling of ..., another exception occurred" stack
        cause = getattr(exc, '__cause__', None)
        context = getattr(exc, '__context__', None)
        exc = cause or context


def format_attrs(obj, ignore_dunder=False):
    for k, v in dump_attrs(obj, ignore_dunder=ignore_dunder):
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
        lines = ["Event Data:"]
        lines.extend(indent(format_attrs(launched_event)))
        _, exc, _ = error

        lines.append("")
        lines.append("Error data:")
        lines.extend(indent(format_error_chain(exc)))

        url = web.paste('\n'.join(lines))
        messages.append("Event: " + url)
    except Exception:
        msg = traceback.format_exc()[-1]
        messages.append(
            "Error occurred while gathering error data {}".format(msg)
        )

    for message in messages:
        admin_log(message, should_broadcast)
