import json
import requests
from requests import HTTPError, RequestException

from cloudbot import hook
from cloudbot.util.web import (
    Pastebin,
    ServiceError,
    ServiceHTTPError,
    pastebins,
)


class Sharey(Pastebin):
    def __init__(self, base_url) -> None:
        super().__init__()
        self.url = base_url

    def paste(self, data, ext) -> str:
        try:
            encoded = json.loads(data)
        except json.JSONDecodeError:
            encoded = {"content": data}

        # params = {
        #     "content": encoded,
        # }

        try:
            with requests.post(self.url, json=encoded) as response:
                response.raise_for_status()
                url = response.json()["url"]
        except HTTPError as e:
            r = e.response
            raise ServiceHTTPError(r.reason, r) from e
        except RequestException as e:
            raise ServiceError(e.request, "Connection error occurred") from e

        if ext:
            url += f"?{ext}"

        return url


@hook.on_start()
def register() -> None:
    pastebins.register("sharey", Sharey("https://sharey.org/api/paste"))


@hook.on_stop()
def unregister() -> None:
    pastebins.remove("sharey")
