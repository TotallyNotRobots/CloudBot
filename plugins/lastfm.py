import math
import string
from datetime import datetime

import requests
from sqlalchemy import Table, Column, PrimaryKeyConstraint, String

from cloudbot import hook
from cloudbot.util import timeformat, web, database

api_url = "http://ws.audioscrobbler.com/2.0/?format=json"

table = Table(
    "lastfm",
    database.metadata,
    Column('nick', String(25)),
    Column('acc', String(25)),
    PrimaryKeyConstraint('nick')
)


def format_user(user):
    return '\u200B'.join((user[:1], user[1:]))


def filter_tags(tags, artist, limit=4):
    """
    Takes a list of tags (strings) and an artist name.
    returns a new list of N tags with the following changes:
     * All lowercase
     * Artist name removed
     * Blacklist of words removed
    """

    # We never want to see these specific tags
    blacklist = [
        "seen live",
    ]

    # Force all tags to lowercase first
    # This allows easy comparisons with artist and blacklist
    tags = [tag.lower() for tag in tags]

    # Remove punctuation marks from artist name and force to lowercase
    # This accounts for inconsistencies in naming, e.g. "Panic! at the disco"
    translator = str.maketrans(dict.fromkeys(string.punctuation))
    artist = artist.translate(translator).lower()

    # Perform the actual filtering, stop when we reach the desired number of tags
    count = 0
    filtered_tags = []
    for tag in tags:
        if not tag == artist:
            if tag not in blacklist:
                filtered_tags.append(tag)
        count += 1
        if count == limit:
            return filtered_tags


last_cache = {}


@hook.on_start()
def load_cache(db):
    """
    :type db: sqlalchemy.orm.Session
    """
    last_cache.clear()
    for row in db.execute(table.select()):
        nick = row["nick"]
        account = row["acc"]
        last_cache[nick] = account


def get_account(nick, text=None):
    """looks in last_cache for the lastfm account name"""
    return last_cache.get(nick.lower(), text)


def api_request(method, api_key, **params):
    params.update({"method": method, "api_key": api_key})
    request = requests.get(api_url, params=params)

    if request.status_code != requests.codes.ok:
        return {}, "Failed to fetch info ({})".format(request.status_code)

    data = request.json()
    if 'error' in data:
        return data, "Error: {}.".format(data["message"])

    return data, None


def get_tags(api_key, method, artist, **params):
    tag_list = []
    tags, err = api_request(method + ".getTopTags", api_key, artist=artist, autocorrect=1, **params)

    # if artist doesn't exist return no tags
    if tags.get("error") == 6:
        return "no tags"

    if 'tag' in tags['toptags']:
        for item in tags['toptags']['tag']:
            tag_list.append(item['name'])

    tag_list = filter_tags(tag_list, artist, limit=4)

    return ', '.join(tag_list) if tag_list else 'no tags'


def getartisttags(api_key, artist):
    """Get tags for [artist]"""
    return get_tags(api_key, "artist", artist)


def gettracktags(api_key, artist, title):
    """Get tags for [title] by [artist]"""
    return get_tags(api_key, "track", artist, track=title)


def getsimilarartists(api_key, artist):
    artist_list = []
    similar, err = api_request('artist.getsimilar', api_key, artist=artist, autocorrect=1)

    # check it's a list
    if isinstance(similar['similarartists']['artist'], list):
        for item in similar['similarartists']['artist']:
            artist_list.append(item['name'])

    artist_list = artist_list[:4]

    return ', '.join(artist_list) if artist_list else 'no similar artists'


def getusertrackplaycount(api_key, artist, track, user):
    track_info, err = api_request("track.getInfo", api_key, artist=artist, track=track, username=user)
    if err and not track_info:
        return err

    # if track doesn't exist return 0 playcount
    if track_info.get("error") == 6:
        return 0

    return track_info['track'].get('userplaycount')


def getartistinfo(api_key, artist, user=''):
    params = {}
    if user:
        params['username'] = user
    artist, err = api_request("artist.getInfo", api_key, artist=artist, autocorrect=1, **params)
    return artist


def _topartists(bot, text, nick, period=None, limit=10):
    api_key = bot.config.get("api_keys", {}).get("lastfm")
    if not api_key:
        return "error: no api key set"

    if text:
        username = get_account(text)
        if not username:
            username = text
    else:
        username = get_account(nick)
    if not username:
        return "No last.fm username specified and no last.fm username is set in the database."
    params = {}
    if period:
        params['period'] = period

    data, err = api_request("user.gettopartists", api_key, user=username, limit=limit, **params)
    if err:
        return err

    artists = data["topartists"]["artist"][:limit]

    out = "{}'s favorite artists: ".format(format_user(username))
    for artist in artists:
        artist_name = artist["name"]
        play_count = artist["playcount"]
        out = out + "{} [{:,}] ".format(artist_name, int(play_count))
    return out


@hook.command("lastfm", "last", "np", "l", autohelp=False)
def lastfm(event, db, text, nick, bot):
    """[user] [dontsave] - displays the now playing (or last played) track of LastFM user [user]"""
    api_key = bot.config.get("api_keys", {}).get("lastfm")
    if not api_key:
        return "error: no api key set"

    # check if the user asked us not to save his details
    dontsave = text.endswith(" dontsave")
    if dontsave:
        user = text[:-9].strip().lower()
    else:
        user = text

    if not user:
        user = get_account(nick)
        if not user:
            event.notice_doc()
            return

    response, err = api_request('user.getrecenttracks', api_key, user=user, limit=1)
    if err:
        return err

    if "track" not in response["recenttracks"] or len(response["recenttracks"]["track"]) == 0:
        return 'No recent tracks for user "{}" found.'.format(format_user(user))

    tracks = response["recenttracks"]["track"]

    if isinstance(tracks, list):
        track = tracks[0]

        if "@attr" in track and "nowplaying" in track["@attr"] and track["@attr"]["nowplaying"] == "true":
            # if the user is listening to something, the first track (a dict) of the
            # tracks list will contain an item with the "@attr" key.
            # this item will will contain another item with the "nowplaying" key
            # which value will be "true"
            status = 'is listening to'
            ending = '.'
        else:
            # otherwise, the user is not listening to anything right now
            status = 'last listened to'
            # lets see how long ago they listened to it
            time_listened = datetime.fromtimestamp(int(track["date"]["uts"]))
            time_since = timeformat.time_since(time_listened)
            ending = ' ({} ago)'.format(time_since)
    else:
        return "error: could not parse track listing"

    title = track["name"]
    album = track["album"]["#text"]
    artist = track["artist"]["#text"]
    url = web.try_shorten(track["url"])

    tags = gettracktags(api_key, artist, title)
    if tags == "no tags":
        tags = getartisttags(api_key, artist)

    playcount = getusertrackplaycount(api_key, artist, title, user)

    out = '{} {} "{}"'.format(format_user(user), status, title)
    if artist:
        out += " by \x02{}\x0f".format(artist)
    if album:
        out += " from the album \x02{}\x0f".format(album)
    if playcount:
        out += " [playcount: {}]".format(playcount)
    else:
        out += " [playcount: 0]"
    if url:
        out += " {}".format(url)

    out += " ({})".format(tags)

    # append ending based on what type it was
    out += ending

    if text and not dontsave:
        if get_account(nick):
            db.execute(table.update().values(acc=user).where(table.c.nick == nick.lower()))
            db.commit()
        else:
            db.execute(table.insert().values(nick=nick.lower(), acc=user))
            db.commit()

        load_cache(db)
    return out


@hook.command("plays")
def getuserartistplaycount(event, bot, text, nick):
    """[artist] - displays the current user's playcount for [artist]. You must have your username saved."""
    api_key = bot.config.get("api_keys", {}).get("lastfm")
    if not api_key:
        return "error: no api key set"

    user = get_account(nick)
    if not user:
        event.notice_doc()
        return

    artist_info = getartistinfo(api_key, text, user)

    if 'error' in artist_info:
        return 'No such artist.'

    if 'userplaycount' not in artist_info['artist']['stats']:
        return '"{}" has never listened to {}.'.format(format_user(user), text)

    playcount = artist_info['artist']['stats']['userplaycount']

    out = '"{}" has {:,} {} plays.'.format(format_user(user), int(playcount), text)

    return out


@hook.command("band", "la")
def displaybandinfo(bot, text):
    """[artist] - displays information about [artist]."""
    api_key = bot.config.get("api_keys", {}).get("lastfm")
    if not api_key:
        return "error: no api key set"

    artist = getartistinfo(api_key, text)

    if 'error' in artist:
        return 'No such artist.'

    a = artist['artist']
    similar = getsimilarartists(api_key, text)
    tags = getartisttags(api_key, text)

    out = "{} has {:,} plays and {:,} listeners.".format(text, int(a['stats']['playcount']),
                                                         int(a['stats']['listeners']))
    out += " Similar artists include {}. Tags: ({}).".format(similar, tags)

    return out


@hook.command("lastfmcompare", "compare", "lc")
def lastfmcompare(bot, text, nick):
    """<user1> [user2] - displays the now playing (or last played) track of LastFM user [user]"""
    api_key = bot.config.get("api_keys", {}).get("lastfm")
    if not api_key:
        return "error: no api key set"

    if not text:
        return "please specify a lastfm username to compare"

    users = text.split(None, 2)
    user1 = users.pop(0)

    if users:
        user2 = users.pop(0)
    else:
        user2 = user1
        user1 = nick

    user2_check = get_account(user2)
    if user2_check:
        user2 = user2_check

    user1_check = get_account(user1)
    if user1_check:
        user1 = user1_check

    data, err = api_request('tasteometer.compare', api_key, type1="user", value1=user1, type2="user", value2=user2)
    if err:
        return err

    score = float(data["comparison"]["result"]["score"])
    score = float("{:.3f}".format(score * 100))
    if score == 0:
        return "{} and {} have no common listening history.".format(format_user(user2), format_user(user1))
    levels = (
        ("Super", 95),
        ("Very High", 80),
        ("High", 60),
        ("Medium", 40),
        ("Low", 10),
        ("Very Low", -math.inf),  # Everything is > -math.inf so this acts as an `else:`
    )
    level = ""
    for name, threshold in levels:
        if score > threshold:
            level = name
            break

    artists = []
    if isinstance(data["comparison"]["result"]["artists"]["artist"], list):
        artists = data["comparison"]["result"]["artists"]["artist"]
    elif "artist" in data["comparison"]["result"]["artists"]:
        artists = [data["comparison"]["result"]["artists"]["artist"]]

    artists = [artist["name"] for artist in artists]

    artist_string = "\x02In Common:\x02 " + ", ".join(artists) if artists else ""

    return "Musical compatibility between \x02{}\x02 and \x02{}\x02: {} (\x02{}%\x02) {}".format(
        format_user(user1), format_user(user2), level, score, artist_string
    )


@hook.command("ltop", "ltt", autohelp=False)
def toptrack(bot, text, nick):
    """[username] - Grabs a list of the top tracks for a last.fm username"""
    api_key = bot.config.get("api_keys", {}).get("lastfm")
    if not api_key:
        return "error: no api key set"

    if text:
        username = get_account(text)
        if not username:
            username = text
    else:
        username = get_account(nick)
    if not username:
        return "No last.fm username specified and no last.fm username is set in the database."

    data, err = api_request("user.gettoptracks", api_key, user=username, limit=5)
    if err:
        return err

    songs = data["toptracks"]["track"][:5]
    out = "{}'s favorite songs: ".format(format_user(username))
    for song in songs:
        track_name = song["name"]
        artist_name = song["artist"]["name"]
        play_count = song["playcount"]
        out = out + "{} by {} listened to {:,} times. ".format(track_name, artist_name, int(play_count))
    return out


@hook.command("lta", "topartist", autohelp=False)
def topartists(bot, text, nick):
    """[username] - Grabs a list of the top artists for a last.fm username. You can set your lastfm username with .l username"""
    return _topartists(bot, text, nick)


@hook.command("ltw", "topweek", autohelp=False)
def topweek(bot, text, nick):
    """[username] - Grabs a list of the top artists in the last week for a last.fm username. You can set your lastfm username with .l username"""
    return _topartists(bot, text, nick, '7day')


@hook.command("ltm", "topmonth", autohelp=False)
def topmonth(bot, text, nick):
    """[username] - Grabs a list of the top artists in the last month for a last.fm username. You can set your lastfm username with .l username"""
    return _topartists(bot, text, nick, '1month')


@hook.command("lty", "topyear", autohelp=False)
def topall(bot, text, nick):
    """[username] - Grabs a list of the top artists in the last year for a last.fm username. You can set your lastfm username with .l username"""
    return _topartists(bot, text, nick, '1year')
