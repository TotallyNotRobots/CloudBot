"""
web.py

Contains functions for interacting with web services.

Created by:
    - Bjorn Neergaard <https://github.com/neersighted>

Maintainer:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""

import json
import logging
import time
from operator import attrgetter
from typing import Dict, Optional

import requests
from requests import HTTPError, PreparedRequest, RequestException, Response

# Constants
DEFAULT_SHORTENER = "is.gd"
DEFAULT_PASTEBIN = ""

HASTEBIN_SERVER = "https://hastebin.com"

logger = logging.getLogger("cloudbot")


# Shortening / pasting

# Public API


class Registry:
    class Item:
        def __init__(self, item):
            self.item = item
            self.working = True
            self.last_check = 0.0
            self.uses = 0

        def failed(self):
            self.working = False
            self.last_check = time.time()

        @property
        def should_use(self):
            if self.working:
                return True

            if (time.time() - self.last_check) > (5 * 60):
                # It's been 5 minutes, try again
                self.working = True
                return True

            return False

    def __init__(self):
        self._items: Dict[str, "Registry.Item"] = {}

    def register(self, name, item):
        if name in self._items:
            raise ValueError("Attempt to register duplicate item")

        self._items[name] = self.Item(item)

    def get(self, name):
        val = self._items.get(name)
        if val:
            return val.item

        return val

    def get_item(self, name):
        return self._items.get(name)

    def get_working(self) -> Optional["Item"]:
        working = [item for item in self._items.values() if item.should_use]

        if not working:
            return None

        return min(working, key=attrgetter("uses"))

    def remove(self, name):
        del self._items[name]

    def items(self):
        return self._items.items()

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, item):
        return self._items[item].item

    def set_working(self):
        for item in self._items.values():
            item.working = True


def shorten(url, custom=None, key=None, service=DEFAULT_SHORTENER):
    impl = shorteners[service]
    return impl.shorten(url, custom, key)


def try_shorten(url, custom=None, key=None, service=DEFAULT_SHORTENER):
    impl = shorteners[service]
    return impl.try_shorten(url, custom, key)


def expand(url, service=None):
    if service:
        impl = shorteners[service]
    else:
        impl = None
        for name in shorteners:
            if name in url:
                impl = shorteners[name]
                break

        if impl is None:
            impl = Shortener()

    return impl.expand(url)


class NoPasteException(Exception):
    """No pastebins succeeded"""


def paste(data, ext="txt", service=DEFAULT_PASTEBIN, raise_on_no_paste=False):
    if service:
        impl = pastebins.get_item(service)
    else:
        impl = pastebins.get_working()

        if not impl:
            pastebins.set_working()
            impl = pastebins.get_working()

    while impl:
        try:
            out = impl.item.paste(data, ext)
            impl.uses += 1
            return out
        except ServiceError:
            impl.failed()
            logger.exception("Paste failed")

        impl = pastebins.get_working()

    if raise_on_no_paste:
        raise NoPasteException("Unable to paste data")

    return "Unable to paste data"


class ServiceError(Exception):
    def __init__(self, request: PreparedRequest, message: str):
        super().__init__(message)
        self.request = request


class ServiceHTTPError(ServiceError):
    def __init__(self, message: str, response: Response):
        super().__init__(
            response.request,
            "[HTTP {}] {}".format(response.status_code, message),
        )
        self.message = message
        self.response = response


class Shortener:
    def __init__(self):
        pass

    def shorten(self, url, custom=None, key=None):
        return url

    def try_shorten(self, url, custom=None, key=None):
        try:
            return self.shorten(url, custom, key)
        except ServiceError:
            return url

    def expand(self, url):
        try:
            r = requests.get(url, allow_redirects=False)
            r.raise_for_status()
        except HTTPError as e:
            r = e.response
            raise ServiceHTTPError(r.reason, r) from e
        except RequestException as e:
            raise ServiceError(e.request, "Connection error occurred") from e

        if "location" in r.headers:
            return r.headers["location"]

        raise ServiceHTTPError("That URL does not exist", r)


class Pastebin:
    def __init__(self):
        pass

    def paste(self, data, ext):
        raise NotImplementedError


shorteners = Registry()
pastebins = Registry()

# Internal Implementations


class Isgd(Shortener):
    def shorten(self, url, custom=None, key=None):
        p = {"url": url, "shorturl": custom, "format": "json"}
        try:
            r = requests.get("https://is.gd/create.php", params=p)
            r.raise_for_status()
        except HTTPError as e:
            r = e.response
            raise ServiceHTTPError(r.reason, r) from e
        except RequestException as e:
            raise ServiceError(e.request, "Connection error occurred") from e

        j = r.json()

        if "shorturl" in j:
            return j["shorturl"]

        raise ServiceHTTPError(j["errormessage"], r)

    def expand(self, url):
        p = {"shorturl": url, "format": "json"}
        try:
            r = requests.get("https://is.gd/forward.php", params=p)
            r.raise_for_status()
        except HTTPError as e:
            r = e.response
            raise ServiceHTTPError(r.reason, r) from e
        except RequestException as e:
            raise ServiceError(e.request, "Connection error occurred") from e

        j = r.json()

        if "url" in j:
            return j["url"]

        raise ServiceHTTPError(j["errormessage"], r)


class Googl(Shortener):
    def shorten(self, url, custom=None, key=None):
        h = {"content-type": "application/json"}
        k = {"key": key}
        p = {"longUrl": url}
        try:
            r = requests.post(
                "https://www.googleapis.com/urlshortener/v1/url",
                params=k,
                data=json.dumps(p),
                headers=h,
            )
            r.raise_for_status()
        except HTTPError as e:
            r = e.response
            raise ServiceHTTPError(r.reason, r) from e
        except RequestException as e:
            raise ServiceError(e.request, "Connection error occurred") from e

        j = r.json()

        if "error" not in j:
            return j["id"]

        raise ServiceHTTPError(j["error"]["message"], r)

    def expand(self, url):
        p = {"shortUrl": url}
        try:
            r = requests.get(
                "https://www.googleapis.com/urlshortener/v1/url", params=p
            )
            r.raise_for_status()
        except HTTPError as e:
            r = e.response
            raise ServiceHTTPError(r.reason, r) from e
        except RequestException as e:
            raise ServiceError(e.request, "Connection error occurred") from e

        j = r.json()

        if "error" not in j:
            return j["longUrl"]

        raise ServiceHTTPError(j["error"]["message"], r)


class Gitio(Shortener):
    def shorten(self, url, custom=None, key=None):
        p = {"url": url, "code": custom}
        try:
            r = requests.post("https://git.io", data=p)
            r.raise_for_status()
        except HTTPError as e:
            r = e.response
            raise ServiceHTTPError(r.reason, r) from e
        except RequestException as e:
            raise ServiceError(e.request, "Connection error occurred") from e

        if r.status_code == requests.codes.created:
            s = r.headers["location"]
            if custom and custom not in s:
                raise ServiceHTTPError("That URL is already in use", r)

            return s

        raise ServiceHTTPError(r.text, r)


class Hastebin(Pastebin):
    def __init__(self, base_url):
        super().__init__()
        self.url = base_url

    def paste(self, data, ext):
        if isinstance(data, str):
            encoded = data.encode()
        else:
            encoded = data

        try:
            r = requests.post(self.url + "/documents", data=encoded)
            r.raise_for_status()
        except HTTPError as e:
            r = e.response
            raise ServiceHTTPError(r.reason, r) from e
        except RequestException as e:
            raise ServiceError(e.request, "Connection error occurred") from e
        else:
            j = r.json()

            if r.status_code is requests.codes.ok:
                return "{}/{}.{}".format(self.url, j["key"], ext)

            raise ServiceHTTPError(j["message"], r)


pastebins.register("hastebin", Hastebin(HASTEBIN_SERVER))

shorteners.register("git.io", Gitio())
shorteners.register("goo.gl", Googl())
shorteners.register("is.gd", Isgd())
