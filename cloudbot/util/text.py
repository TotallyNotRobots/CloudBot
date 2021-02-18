from typing import Optional

__all__ = ("parse_bool",)

_STR_TO_BOOL = {
    "yes": True,
    "y": True,
    "no": False,
    "n": False,
    "on": True,
    "off": False,
    "enable": True,
    "disable": False,
    "allow": True,
    "deny": False,
    "true": True,
    "false": False,
}


def parse_bool(s: str, *, fail_on_unknown: bool = True) -> Optional[bool]:
    """
    Parse a string to a boolean value

    >>> parse_bool('true')
    True
    >>> parse_bool('yes')
    True
    >>> parse_bool('no')
    False
    >>> parse_bool('maybe', fail_on_unknown=False)
    >>> parse_bool('maybe')
    Traceback (most recent call last):
        [...]
    KeyError: 'maybe'

    :param s: The string to parse
    :param fail_on_unknown: Whether to raise an error if the input can't
        be parsed
    :return: The parsed value
    """

    try:
        return _STR_TO_BOOL[s.lower()]
    except KeyError:
        if fail_on_unknown:
            raise

        return None
