import re
from datetime import datetime, timedelta
from threading import RLock

import requests
from requests import HTTPError
from requests.auth import HTTPBasicAuth
from yarl import URL

from cloudbot import hook

api = None

spotify_re = re.compile(
    r'(spotify:(track|album|artist|user):([a-zA-Z0-9]+))', re.I
)
http_re = re.compile(
    r'(open\.spotify\.com/(track|album|artist|user)/([a-zA-Z0-9]+))', re.I
)

TYPE_MAP = {
    'artist': 'artists',
    'album': 'albums',
    'track': 'tracks',
}


class SpotifyAPI:
    api_url = URL("https://api.spotify.com/v1")
    token_refresh_url = URL("https://accounts.spotify.com/api/token")

    def __init__(self, client_id=None, client_secret=None):
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = None
        self._token_expires = datetime.min
        self._lock = RLock()  # Make sure only one requests is parsed at a time

    def request(self, endpoint, params=None):
        with self._lock:
            if datetime.now() >= self._token_expires:
                self._refresh_token()

            r = requests.get(
                self.api_url / endpoint, params=params, headers={'Authorization': 'Bearer ' + self._access_token}
            )
            r.raise_for_status()

            return r

    def search(self, params):
        return self.request('search', params)

    def _refresh_token(self):
        with self._lock:
            basic_auth = HTTPBasicAuth(self._client_id, self._client_secret)
            gtcc = {"grant_type": "client_credentials"}
            r = requests.post(self.token_refresh_url, data=gtcc, auth=basic_auth)
            r.raise_for_status()
            auth = r.json()
            self._access_token = auth["access_token"]
            self._token_expires = datetime.now() + timedelta(seconds=auth["expires_in"])


def _search(text, _type, reply):
    params = {"q": text.strip(), "offset": 0, "limit": 1, "type": _type}

    try:
        request = api.search(params)
    except HTTPError as e:
        reply("Could not get track information: {}".format(e.request.status_code))
        raise

    return request.json()[TYPE_MAP[_type]]["items"][0]


@hook.onload
def create_api(bot):
    keys = bot.config['api_keys']
    client_id = keys['spotify_client_id']
    client_secret = keys['spotify_client_secret']
    global api
    api = SpotifyAPI(client_id, client_secret)


@hook.command('spotify', 'sptrack')
def spotify(text, reply):
    """<song> - Search Spotify for <song>"""
    data = _search(text, "track", reply)

    try:
        return "\x02{}\x02 by \x02{}\x02 - {} / {}".format(
            data["name"], data["artists"][0]["name"],
            data["external_urls"]["spotify"], data["uri"])
    except IndexError:
        return "Unable to find any tracks!"


@hook.command("spalbum")
def spalbum(text, reply):
    """<album> - Search Spotify for <album>"""
    data = _search(text, "album", reply)

    try:
        return "\x02{}\x02 by \x02{}\x02 - {} / {}".format(
            data["artists"][0]["name"], data["name"],
            data["external_urls"]["spotify"], data["uri"])
    except IndexError:
        return "Unable to find any albums!"


@hook.command("spartist", "artist")
def spartist(text, reply):
    """<artist> - Search Spotify for <artist>"""
    data = _search(text, "artist", reply)

    try:
        return "\x02{}\x02 - {} / {}".format(
            data["name"], data["external_urls"]["spotify"], data["uri"])
    except IndexError:
        return "Unable to find any artists!"


@hook.regex(http_re)
@hook.regex(spotify_re)
def spotify_url(match):
    _type = match.group(2)
    spotify_id = match.group(3)

    request = api.request("{}/{}".format(TYPE_MAP[_type], spotify_id))

    data = request.json()

    if _type == "track":
        name = data["name"]
        artist = data["artists"][0]["name"]
        album = data["album"]["name"]

        return "Spotify Track: \x02{}\x02 by \x02{}\x02 from the album \x02{}\x02".format(name, artist, album)
    elif _type == "artist":
        return "Spotify Artist: \x02{}\x02, followers: \x02{}\x02, genres: \x02{}\x02".format(
            data["name"], data["followers"]["total"],
            ', '.join(data["genres"]))
    elif _type == "album":
        return "Spotify Album: \x02{}\x02 - \x02{}\x02".format(data["artists"][0]["name"], data["name"])
