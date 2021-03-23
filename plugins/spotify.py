import re
from datetime import datetime, timedelta
from threading import RLock

import requests
from requests import HTTPError
from requests.auth import HTTPBasicAuth
from yarl import URL

from cloudbot import hook
from cloudbot.bot import bot

spotify_re = re.compile(
    r"(spotify:(track|album|artist|user):([a-zA-Z0-9]+))", re.I
)
http_re = re.compile(
    r"(open\.spotify\.com/(track|album|artist|user)/([a-zA-Z0-9]+))", re.I
)

TYPE_MAP = {
    "artist": "artists",
    "album": "albums",
    "track": "tracks",
    "user": "users",
}

NO_RESULTS = "Unable to find matching {type}"


class SpotifyAPI:
    api_url = URL("https://api.spotify.com/v1")
    token_refresh_url = URL("https://accounts.spotify.com/api/token")

    def __init__(self, client_id=None, client_secret=None):
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = None
        self._token_expires = datetime.min
        self._lock = RLock()  # Make sure only one requests is parsed at a time

    def set_keys(self, client_id, client_secret):
        self._client_id = client_id
        self._client_secret = client_secret

        if self:
            self._refresh_token()

    def __bool__(self):
        return bool(self._client_id and self._client_secret)

    def request(self, endpoint, params=None):
        with self._lock:
            if datetime.now() >= self._token_expires:
                self._refresh_token()

            with requests.get(
                self.api_url / endpoint,
                params=params,
                headers={"Authorization": "Bearer " + self._access_token},
            ) as r:
                r.raise_for_status()

            return r

    def search(self, params):
        return self.request("search", params)

    def _refresh_token(self):
        with self._lock:
            basic_auth = HTTPBasicAuth(self._client_id, self._client_secret)
            gtcc = {"grant_type": "client_credentials"}
            r = requests.post(
                str(self.token_refresh_url), data=gtcc, auth=basic_auth
            )
            r.raise_for_status()
            auth = r.json()
            self._access_token = auth["access_token"]
            self._token_expires = datetime.now() + timedelta(
                seconds=auth["expires_in"]
            )


api = SpotifyAPI()


def _search(text, _type, reply):
    params = {"q": text.strip(), "offset": 0, "limit": 1, "type": _type}

    try:
        request = api.search(params)
    except HTTPError as e:
        reply(
            "Could not get track information: {}".format(e.response.status_code)
        )
        raise

    results = request.json()[TYPE_MAP[_type]]["items"]

    if not results:
        return None

    return results[0]


FORMATS = {
    "track": (
        "\x02{display_name}\x02 by \x02{main_artist[name]}\x02 "
        "from the album \x02{album[name]}\x02"
    ),
    "artist": (
        "\x02{display_name}\x02, followers: \x02{followers[total]}\x02, "
        "genres: \x02{genre_str}\x02"
    ),
    "album": "\x02{main_artist[name]}\x02 - \x02{display_name}\x02",
    "user": "\x02{display_name}\x02, Followers: \x02{followers[total]:,d}\x02",
}


def _do_format(data, _type):
    if "display_name" not in data:
        data["display_name"] = data["name"]

    if "genres" in data:
        data["genre_str"] = ", ".join(data["genres"])

    if "artists" in data:
        data["main_artist"] = data["artists"][0]

    if _type in FORMATS:
        fmt = FORMATS[_type]
        return "Spotify {}".format(_type.title()), fmt.format_map(data)

    raise ValueError("Attempt to format unknown Spotify API type: " + _type)


def _format_response(
    data, _type, show_pre=False, show_url=False, show_uri=False
):
    pre, text = _do_format(data, _type)
    if show_pre:
        out = pre + ": "
    else:
        out = ""

    out += text

    if show_uri or show_url:
        out += " -"

    if show_url:
        out += " " + data["external_urls"]["spotify"]

    if show_uri:
        out += " " + "[{}]".format(data["uri"])

    return out


def _format_search(text, _type, reply):
    data = _search(text, _type, reply)
    if data is None:
        return NO_RESULTS.format(type=_type)

    return _format_response(data, _type, show_url=True, show_uri=True)


@hook.on_start()
def set_keys():
    api.set_keys(
        bot.config.get_api_key("spotify_client_id"),
        bot.config.get_api_key("spotify_client_secret"),
    )


@hook.command("spotify", "sptrack")
def spotify(text, reply):
    """<song> - Search Spotify for <song>"""
    return _format_search(text, "track", reply)


@hook.command("spalbum")
def spalbum(text, reply):
    """<album> - Search Spotify for <album>"""
    return _format_search(text, "album", reply)


@hook.command("spartist", "artist")
def spartist(text, reply):
    """<artist> - Search Spotify for <artist>"""
    return _format_search(text, "artist", reply)


@hook.regex(http_re)
@hook.regex(spotify_re)
def spotify_url(match):
    _type = match.group(2)
    spotify_id = match.group(3)

    request = api.request("{}/{}".format(TYPE_MAP[_type], spotify_id))

    data = request.json()

    return _format_response(data, _type, show_pre=True)
