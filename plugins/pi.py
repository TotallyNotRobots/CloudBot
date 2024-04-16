# Get range of pi digits
import requests

from cloudbot import hook

API = "https://api.pi.delivery/v1/pi"
MAX_DIGITS = 400


def pi_range(start: int, size: int) -> str:
    response = requests.get(
        API, params={"start": start, "numberOfDigits": size, "radix": 10}
    )
    if response.status_code == 200:
        yield response.json().get("content")


@hook.command("pi", autohelp=False)
def pi(text: str):
    """<start> <size> - Gets the first <size> digits of pi starting at <start>"""
    try:
        start, size = text.split()
    except ValueError:
        size = MAX_DIGITS
        if text:
            start = text
        else:
            start = 0
    try:
        start = int(start)
        size = int(size)
    except ValueError:
        return "Usage: .pi <start> <size>"

    if size > MAX_DIGITS:
        return f"Size must be less than {MAX_DIGITS}"
    if size < 0:
        return "Size must be greater than 0"

    if start < 0:
        return "Start must be greater than 0"

    return "".join(pi_range(start, size))
