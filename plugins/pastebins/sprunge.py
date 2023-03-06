import requests
from requests import HTTPError, RequestException

from cloudbot import hook
from cloudbot.util.web import (
    Pastebin,
    ServiceError,
    ServiceHTTPError,
    pastebins,
)


class Sprunge(Pastebin):
    def __init__(self, base_url):
        super().__init__()
        self.url = base_url

    def paste(self, data, ext):
        if isinstance(data, str):
            encoded = data.encode()
        else:
            encoded = data

        params = {
            "sprunge": encoded,
        }

        try:
            with requests.post(self.url, data=params) as response:
                response.raise_for_status()
                url = response.text.strip()
        except HTTPError as e:
            r = e.response
            raise ServiceHTTPError(r.reason, r) from e
        except RequestException as e:
            raise ServiceError(e.request, "Connection error occurred") from e

        if ext:
            url += "?{}".format(ext)

        return url


@hook.on_start()
def register():
    pastebins.register("sprunge", Sprunge("https://sprunge.us"))


@hook.on_stop()
def unregister():
    pastebins.remove("sprunge")
