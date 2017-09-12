import re
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

from cloudbot import hook

api_url = "https://api.spotify.com/v1/search?"
token_url = "https://accounts.spotify.com/api/token"
spuri = 'spotify:{}:{}'
access_token = ""
expires_at = datetime.min

spotify_re = re.compile(r'(spotify:(track|album|artist|user):([a-zA-Z0-9]+))',
                        re.I)
http_re = re.compile(r'(open\.spotify\.com/(track|album|artist|user)/'
                     '([a-zA-Z0-9]+))', re.I)


def sprequest(bot, params, alturl=None):
    global access_token, expires_at
    if alturl == None:
        alturl = api_url
    if datetime.now() >= expires_at:
        basic_auth = HTTPBasicAuth(
            bot.config.get("api_keys", {}).get("spotify_client_id"),
            bot.config.get("api_keys", {}).get("spotify_client_secret"))
        gtcc = {"grant_type": "client_credentials"}
        auth = requests.post(token_url, data=gtcc, auth=basic_auth).json()
        if 'access_token' in auth.keys():
            access_token = auth["access_token"]
            expires_at = datetime.fromtimestamp(datetime.now().timestamp() +
                                                auth["expires_in"])
    headers = {'Authorization': 'Bearer ' + access_token}
    return requests.get(alturl, params=params, headers=headers)


@hook.command('spotify', 'sptrack')
def spotify(bot, text):
    """spotify <song> -- Search Spotify for <song>"""
    params = {"q": text.strip(), "offset": 0, "limit": 1, "type": "track"}

    request = sprequest(bot, params)
    if request.status_code != requests.codes.ok:
        return "Could not get track information: {}".format(
            request.status_code)

    data = request.json()["tracks"]["items"][0]

    try:
        return "\x02{}\x02 by \x02{}\x02 - {} / {}".format(
            data["artists"][0]["name"], data["external_urls"]["spotify"],
            data["name"], data["uri"])
    except IndexError:
        return "Unable to find any tracks!"


@hook.command("spalbum")
def spalbum(bot, text):
    """spalbum <album> -- Search Spotify for <album>"""
    params = {"q": text.strip(), "offset": 0, "limit": 1, "type": "album"}

    request = sprequest(bot, params)
    if request.status_code != requests.codes.ok:
        return "Could not get album information: {}".format(
            request.status_code)

    data = request.json()["albums"]["items"][0]

    try:
        return "\x02{}\x02 by \x02{}\x02 - {} / {}".format(
            data["artists"][0]["name"], data["name"],
            data["external_urls"]["spotify"], data["uri"])
    except IndexError:
        return "Unable to find any albums!"


@hook.command("spartist", "artist")
def spartist(bot, text):
    """spartist <artist> -- Search Spotify for <artist>"""
    params = {"q": text.strip(), "offset": 0, "limit": 1, "type": "artist"}

    request = sprequest(bot, params)
    if request.status_code != requests.codes.ok:
        return "Could not get artist information: {}".format(
            request.status_code)

    data = request.json()["artists"]["items"][0]

    try:
        return "\x02{}\x02 - {} / {}".format(
            data["name"], data["external_urls"]["spotify"], data["uri"])
    except IndexError:
        return "Unable to find any artists!"


@hook.regex(http_re)
@hook.regex(spotify_re)
def spotify_url(bot, match):
    api_method = {'track': 'tracks', 'album': 'albums', 'artist': 'artists'}
    _type = match.group(2)
    spotify_id = match.group(3)
    url = spuri.format(_type, spotify_id)
    # no error catching here, if the API is down fail silently
    request = sprequest(bot, {}, 'http://api.spotify.com/v1/{}/{}'.format(
        api_method[_type], spotify_id))
    if request.status_code != requests.codes.ok:
        return
    data = request.json()
    if _type == "track":
        name = data["name"]
        artist = data["artists"][0]["name"]
        album = data["album"]["name"]
        url = data['external_urls']['spotify']

        return "Spotify Track: \x02{}\x02 by \x02{}\x02 from the album \x02{}\x02 {}".format(
            name, artist, album, url)
    elif _type == "artist":
        return "Spotify Artist: \x02{}\x02, followers: \x02{}\x02, genres: \x02{}\x02".format(
            data["name"], data["followers"]["total"],
            ', '.join(data["genres"]))
    elif _type == "album":
        return "Spotify Album: \x02{}\x02 - \x02{}\x02 {}".format(
            data["artists"][0]["name"], data["name"],
            data['external_urls']['spotify'])
