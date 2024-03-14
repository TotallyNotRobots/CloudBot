import math
import string
from datetime import datetime
from json import JSONDecodeError
from typing import Dict

import requests
from sqlalchemy import Column, PrimaryKeyConstraint, String, Table

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util import database, timeformat, web

api_url = "https://ws.audioscrobbler.com/2.0/?format=json"

table = Table(
    "lastfm",
    database.metadata,
    Column("nick", String),
    Column("acc", String),
    PrimaryKeyConstraint("nick"),
)


def format_user(user):
    """
    >>> format_user('someuser')
    's\u200bomeuser'
    """
    return "\u200B".join((user[:1], user[1:]))


def filter_tags(tags, artist, limit=4):
    """
    Takes a list of tags (strings) and an artist name.
    returns a new list of N tags with the following changes:
     * All lowercase
     * Artist name removed
     * Blacklist of words removed

    >>> filter_tags(['sometag', 'artist', 'seen live', 'Some RaNDoM tAG',
    ... 'tag5', 'tag6', 'tag7'], 'artist')
    ['sometag', 'some random tag', 'tag5', 'tag6']
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
    filtered_tags = []
    for tag in tags:
        if not tag == artist and tag not in blacklist:
            filtered_tags.append(tag)

        if len(filtered_tags) >= limit:
            break

    return filtered_tags


last_cache: Dict[str, str] = {}


@hook.on_start()
def load_cache(db):
    new_cache = {}
    for row in db.execute(table.select()):
        nick = row["nick"]
        account = row["acc"]
        new_cache[nick] = account

    last_cache.clear()
    last_cache.update(new_cache)


def get_account(nick, text=None):
    """looks in last_cache for the lastfm account name"""
    return last_cache.get(nick.lower(), text)


def api_request(method, **params):
    api_key = bot.config.get_api_key("lastfm")
    params.update({"method": method, "api_key": api_key})
    request = requests.get(api_url, params=params)

    try:
        data = request.json()
    except JSONDecodeError:
        # Raise an exception if the HTTP request returned an error
        request.raise_for_status()

        # If raise_for_status() doesn't raise an exception, just re-reraise the
        # existing error
        raise

    if "error" in data:
        return data, "Error: {}.".format(data["message"])

    return data, None


def get_tags(method, artist, **params):
    tag_list = []
    tags, _ = api_request(
        method + ".getTopTags", artist=artist, autocorrect=1, **params
    )

    # if artist doesn't exist return no tags
    if tags.get("error") == 6:
        return "no tags"

    if "tag" in tags["toptags"]:
        for item in tags["toptags"]["tag"]:
            tag_list.append(item["name"])

    tag_list = filter_tags(tag_list, artist)

    return ", ".join(tag_list) if tag_list else "no tags"


def getartisttags(artist):
    """Get tags for [artist]"""
    return get_tags("artist", artist)


def gettracktags(artist, title):
    """Get tags for [title] by [artist]"""
    return get_tags("track", artist, track=title)


def getsimilarartists(artist):
    artist_list = []
    similar, _ = api_request("artist.getsimilar", artist=artist, autocorrect=1)

    # check it's a list
    if isinstance(similar["similarartists"]["artist"], list):
        for item in similar["similarartists"]["artist"]:
            artist_list.append(item["name"])

    artist_list = artist_list[:4]

    return ", ".join(artist_list) if artist_list else "no similar artists"


def getusertrackplaycount(artist, track, user):
    track_info, err = api_request(
        "track.getInfo", artist=artist, track=track, username=user
    )
    if err and not track_info:
        return err

    # if track doesn't exist return 0 playcount
    if track_info.get("error") == 6:
        return 0

    return track_info["track"].get("userplaycount")


def getartistinfo(artist, user=""):
    params = {}
    if user:
        params["username"] = user
    artist, _ = api_request(
        "artist.getInfo", artist=artist, autocorrect=1, **params
    )
    return artist


def check_key_and_user(nick, text):
    """
    Verify an API key is set and perform basic user lookups

    Used as a prerequisite for multiple API commands

    :param nick: The nick of the calling user
    :param text: The text passed to the command, possibly a different username to use
    :return: The parsed username and any error message that occurred
    """
    api_key = bot.config.get_api_key("lastfm")
    if not api_key:
        return None, "Error: No API key set."

    username = text or get_account(nick)

    if not username:
        return (
            None,
            "No last.fm username specified and no last.fm username is set in the database.",
        )

    return username, None


def _topartists(text, nick, period=None, limit=10):
    username, err = check_key_and_user(nick, text)
    if err:
        return err

    params = {}
    if period:
        params["period"] = period

    data, err = api_request(
        "user.gettopartists", user=username, limit=limit, **params
    )
    if err:
        return err

    artists = data["topartists"]["artist"][:limit]

    out = "{}'s favorite artists: ".format(format_user(username))
    for artist in artists:
        artist_name = artist["name"]
        play_count = artist["playcount"]
        out += "{} [{:,}] ".format(artist_name, int(play_count))
    return out


@hook.command("lastfm", "last", "np", "l", autohelp=False)
def lastfm(event, db, text, nick):
    """[user] [dontsave] - displays the now playing (or last played) track of LastFM user [user]"""
    api_key = bot.config.get_api_key("lastfm")
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
            return None

    response, err = api_request("user.getrecenttracks", user=user, limit=1)
    if err:
        return err

    if (
        "track" not in response["recenttracks"]
        or not response["recenttracks"]["track"]
    ):
        return 'No recent tracks for user "{}" found.'.format(format_user(user))

    tracks = response["recenttracks"]["track"]

    if isinstance(tracks, list):
        track = tracks[0]

        if (
            "@attr" in track
            and "nowplaying" in track["@attr"]
            and track["@attr"]["nowplaying"] == "true"
        ):
            # if the user is listening to something, the first track (a dict) of the
            # tracks list will contain an item with the "@attr" key.
            # this item will will contain another item with the "nowplaying" key
            # which value will be "true"
            status = "is listening to"
            ending = "."
        else:
            # otherwise, the user is not listening to anything right now
            status = "last listened to"
            # lets see how long ago they listened to it
            time_listened = datetime.fromtimestamp(int(track["date"]["uts"]))
            time_since = timeformat.time_since(time_listened)
            ending = " ({} ago)".format(time_since)
    else:
        return "error: could not parse track listing"

    title = track["name"]
    album = track["album"]["#text"]
    artist = track["artist"]["#text"]
    url = web.try_shorten(track["url"])

    tags = gettracktags(artist, title)
    if tags == "no tags":
        tags = getartisttags(artist)

    playcount = getusertrackplaycount(artist, title, user)

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
            db.execute(
                table.update()
                .values(acc=user)
                .where(table.c.nick == nick.lower())
            )
            db.commit()
        else:
            db.execute(table.insert().values(nick=nick.lower(), acc=user))
            db.commit()

        load_cache(db)
    return out


@hook.command("plays")
def getuserartistplaycount(event, text, nick):
    """[artist] - displays the current user's playcount for [artist]. You must have your username saved."""
    api_key = bot.config.get_api_key("lastfm")
    if not api_key:
        return "error: no api key set"

    user = get_account(nick)
    if not user:
        event.notice_doc()
        return None

    artist_info = getartistinfo(text, user)

    if "error" in artist_info:
        return "No such artist."

    if "userplaycount" not in artist_info["artist"]["stats"]:
        return '"{}" has never listened to {}.'.format(format_user(user), text)

    playcount = artist_info["artist"]["stats"]["userplaycount"]

    out = '"{}" has {:,} {} plays.'.format(
        format_user(user), int(playcount), text
    )

    return out


@hook.command("band", "la")
def displaybandinfo(text):
    """[artist] - displays information about [artist]."""
    api_key = bot.config.get_api_key("lastfm")
    if not api_key:
        return "error: no api key set"

    artist = getartistinfo(text)

    if "error" in artist:
        return "No such artist."

    a = artist["artist"]
    similar = getsimilarartists(text)
    tags = getartisttags(text)

    out = "{} has {:,} plays and {:,} listeners.".format(
        text, int(a["stats"]["playcount"]), int(a["stats"]["listeners"])
    )
    out += " Similar artists include {}. Tags: ({}).".format(similar, tags)

    return out


@hook.command("lastfmcompare", "compare", "lc")
def lastfmcompare(text, nick):
    """<user1> [user2] - displays the now playing (or last played) track of LastFM user [user]"""
    api_key = bot.config.get_api_key("lastfm")
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

    data, err = api_request(
        "tasteometer.compare",
        type1="user",
        value1=user1,
        type2="user",
        value2=user2,
    )
    if err:
        return err

    score = float(data["comparison"]["result"]["score"])
    score = float("{:.3f}".format(score * 100))
    if score == 0:
        return "{} and {} have no common listening history.".format(
            format_user(user2), format_user(user1)
        )
    levels = (
        ("Super", 95),
        ("Very High", 80),
        ("High", 60),
        ("Medium", 40),
        ("Low", 10),
        # Everything is > -math.inf so this acts as an `else:`
        (
            "Very Low",
            -math.inf,
        ),
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

    artist_string = (
        "\x02In Common:\x02 " + ", ".join(artists) if artists else ""
    )

    return "Musical compatibility between \x02{}\x02 and \x02{}\x02: {} (\x02{}%\x02) {}".format(
        format_user(user1), format_user(user2), level, score, artist_string
    )


@hook.command("ltop", "ltt", autohelp=False)
def toptrack(text, nick):
    """[username] - Grabs a list of the top tracks for a last.fm username"""
    username, err = check_key_and_user(nick, text)
    if err:
        return err

    data, err = api_request("user.gettoptracks", user=username, limit=5)
    if err:
        return err

    songs = data["toptracks"]["track"][:5]
    out = "{}'s favorite songs: ".format(format_user(username))
    for song in songs:
        track_name = song["name"]
        artist_name = song["artist"]["name"]
        play_count = song["playcount"]
        out += "{} by {} listened to {:,} times. ".format(
            track_name, artist_name, int(play_count)
        )
    return out


@hook.command("lta", "topartist", autohelp=False)
def topartists(text, nick):
    """[username] - Grabs a list of the top artists for a last.fm username. You can set your lastfm username with
    .l username"""
    return _topartists(text, nick)


@hook.command("ltw", "topweek", autohelp=False)
def topweek(text, nick):
    """[username] - Grabs a list of the top artists in the last week for a last.fm username. You can set your lastfm
    username with .l username"""
    return _topartists(text, nick, "7day")


@hook.command("ltm", "topmonth", autohelp=False)
def topmonth(text, nick):
    """[username] - Grabs a list of the top artists in the last month for a last.fm username. You can set your lastfm
    username with .l username"""
    return _topartists(text, nick, "1month")


@hook.command("lty", "topyear", autohelp=False)
def topall(text, nick):
    """[username] - Grabs a list of the top artists in the last year for a last.fm username. You can set your lastfm
    username with .l username"""
    return _topartists(text, nick, "1year")
