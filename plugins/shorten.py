from cloudbot import hook
from cloudbot.util import web


@hook.command()
def shorten(text, reply):
    """<url> [custom] - shortens a url with [custom] as an optional custom shortlink"""
    args = text.split()
    url = args[0]
    custom = args[1] if len(args) > 1 else None

    try:
        return web.shorten(url, custom=custom)
    except web.ServiceError as e:
        reply(str(e))
        raise


@hook.command()
def expand(text, reply):
    """<url> - unshortens <url>"""
    args = text.split()
    url = args[0]

    try:
        return web.expand(url)
    except web.ServiceError as e:
        reply(str(e))
        raise


@hook.command()
def isgd(text, reply):
    """<url> [custom] - shortens a url using is.gd with [custom] as an optional custom shortlink,
    or unshortens <url> if already short"""
    args = text.split()
    url = args[0]
    custom = args[1] if len(args) > 1 else None

    try:
        if "is.gd" in url:
            return web.expand(url, "is.gd")

        return web.shorten(url, custom=custom, service="is.gd")
    except web.ServiceError as e:
        reply(str(e))
        raise


@hook.command()
def googl(text, reply):
    """<url> [custom] - shorten <url> using goo.gl with [custom] as an option custom shortlink,
    or unshortens <url> if already short"""
    args = text.split()
    url = args[0]
    custom = args[1] if len(args) > 1 else None

    try:
        if "goo.gl" in url:
            return web.expand(url, "goo.gl")

        return web.shorten(url, custom=custom, service="goo.gl")
    except web.ServiceError as e:
        reply(str(e))
        raise


@hook.command()
def gitio(text, reply):
    """<url> [custom] - shortens a github URL <url> using git.io with [custom] as an optional custom shortlink,
    or unshortens <url> if already short"""
    args = text.split()
    url = args[0]
    custom = args[1] if len(args) > 1 else None

    try:
        if "git.io" in url:
            return web.expand(url, "git.io")

        return web.shorten(url, custom=custom, service="git.io")
    except web.ServiceError as e:
        reply(str(e))
        raise
