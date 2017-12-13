import asyncio

from cloudbot import hook
from cloudbot.util import web


@asyncio.coroutine
@hook.command("python", "py")
def python():
    """<python code> - executes <python code> using eval.appspot.com"""
    return "This API has been deprecated and removed."

    output = yield from web.pyeval(text, pastebin=False)

    if '\n' in output:
        if 'Traceback (most recent call last):' in output:
            status = 'Error: '
        else:
            status = 'Success: '
        return status + web.paste(output)
    else:
        return output
