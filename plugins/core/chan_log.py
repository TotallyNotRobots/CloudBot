import traceback
from typing import Any, Iterable, List, Tuple

from requests.exceptions import RequestException

from cloudbot import hook
from cloudbot.util import web


def get_attrs(obj: object) -> List[str]:
    """Returns a list of all of the attributes on an object,
    either from the __dict__ or from dir() if the object has no __dict__

    >>> class C:
    ...     a = 1
    ...     b = 2
    >>> [name for name in get_attrs(C()) if not is_dunder(name)]
    ['a', 'b']

    And with __slots__:

    >>> class C:
    ...     __slots__ = ('a', 'b')
    ...
    ...     def __init__(self):
    ...         self.a = 1
    ...         self.b = 1
    >>> [name for name in get_attrs(C()) if not is_dunder(name)]
    ['a', 'b']

    :param obj: The object to retrieve the attribute names from
    :return: A list of all attributes on `obj`
    """
    return dir(obj)


def is_dunder(name: str) -> bool:
    """
    Determines if a name represents a "dunder" (double underscore) method

    >>> is_dunder('__iter__')
    True
    >>> is_dunder('some_func')
    False

    :param name: The name to check
    :return: True if the name is a dunder, False otherwise
    """
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


AttrList = Iterable[Tuple[str, Any]]


def dump_attrs(obj: object, ignore_dunder: bool = False) -> AttrList:
    """
    Dump a list of tuples of (name, value) for all attributes on an object

    >>> class C:
    ...     a = 1
    ...     b = 2
    >>> list(dump_attrs(C(), True))
    [('a', 1), ('b', 2)]

    And with __slots__:

    >>> class C:
    ...     __slots__ = ('a', 'b')
    ...
    ...     def __init__(self):
    ...         self.a = 1
    ...         self.b = 2

    >>> list(dump_attrs(C(), True))
    [('a', 1), ('b', 2)]

    :param obj: The object to retrieve attributes from
    :param ignore_dunder: Whether to ignore "dunder" fields and methods
    :return: An iterable of (name, value) tuples for each attribute on `obj`
    """
    for name in get_attrs(obj):
        if ignore_dunder and is_dunder(name):
            # Ignore dunder fields
            continue

        yield (name, getattr(obj, name, None))


def indent(lines: Iterable[str], size: int = 2, char: str = " "):
    """
    Indent each line in an iterable and yield it, ignoring blank lines

    >>> list(indent(['a', 'b', '', 'c']))
    ['  a', '  b', '', '  c']

    :param lines: The iterable of lines to indent
    :param size: How large of an indent should be used
    :param char: What character should be used to indent
    :return: An iterable containing each line from `lines`, indented
    """
    for line in lines:
        if line:
            yield (char * size) + line
        else:
            yield line


def format_requests_exc(exc: RequestException) -> Iterable[str]:
    """
    Format a RequestException
    :param exc: The exception to format
    :return: An iterable of lines representing the formatted data
    """

    def _format(title, obj):
        if obj is not None:
            yield title
            yield from indent(format_attrs(obj))

    yield from _format("Request Info", exc.request)
    yield from _format("Response Info", exc.response)


SPECIAL_CASES = {
    RequestException: format_requests_exc,
}


def format_error_data(exc: Exception) -> Iterable[str]:
    yield repr(exc)
    yield from indent(format_attrs(exc, ignore_dunder=True))

    for typ, func in SPECIAL_CASES.items():
        if isinstance(exc, typ):
            yield from indent(func(exc))

    yield ""


def format_error_chain(exc: Exception) -> Iterable[str]:
    """
    Format a whole chain of exceptions, going up the list for
    each cause/context exception

    :param exc: The exception to format
    :return: An iterable of lines of the formatted data from the exception
    """
    while exc:
        yield from format_error_data(exc)
        # Get "direct cause of" or
        # "during handling of ..., another exception occurred" stack
        cause = getattr(exc, "__cause__", None)
        context = getattr(exc, "__context__", None)
        exc = cause or context


def format_attrs(obj: object, ignore_dunder: bool = False) -> Iterable[str]:
    """
    Format an object's attributes in an easy to read, multi-line format

    >>> class C:
    ...     a = 1
    ...     b = 2
    >>> list(format_attrs(C, True))
    ['a = 1', 'b = 2']

    :param obj: The object to inspect
    :param ignore_dunder: Whether to hide dunder methods/fields
    :return: An iterable of lines of formatted data
    """
    for k, v in dump_attrs(obj, ignore_dunder=ignore_dunder):
        yield "{} = {!r}".format(k, v)


@hook.post_hook()
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
        messages.append("Error occurred while formatting error {}".format(msg))
    else:
        try:
            url = web.paste("\n".join(lines))
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

        url = web.paste("\n".join(lines))
        messages.append("Event: " + url)
    except Exception:
        msg = traceback.format_exc()[-1]
        messages.append(
            "Error occurred while gathering error data {}".format(msg)
        )

    for message in messages:
        admin_log(message, should_broadcast)
