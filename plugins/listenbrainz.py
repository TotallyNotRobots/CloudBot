"""listenbrainz - displays the now playing (or last played) track of a ListenBrainz user.

The plugin remembers each user's ListenBrainz username in the database, so
after the first run the user does not need to supply it every time.
"""
from __future__ import annotations

from datetime import datetime

import requests
from json import JSONDecodeError
from sqlalchemy import Column, PrimaryKeyConstraint, String, Table

from cloudbot import hook
from cloudbot.util import database, timeformat

api_url = "https://api.listenbrainz.org/1"


table = Table(
    "listenbrainz",
    database.metadata,
    Column("nick", String),
    Column("acc", String),
    PrimaryKeyConstraint("nick"),
)


listen_cache: dict[str, str] = {}


def format_user(user: str) -> str:
    """
    >>> format_user('someuser')
    's\u200bomeuser'
    """
    return f"{user[:1]}\u200b{user[1:]}"


@hook.on_start()
def load_cache(db) -> None:
    new_cache = {}
    for row in db.execute(table.select()):
        new_cache[row.nick] = row.acc

    listen_cache.clear()
    listen_cache.update(new_cache)


def get_account(nick, text=None):
    """look in listen_cache for the ListenBrainz account name"""
    return listen_cache.get(nick.lower(), text)


def api_request(path, **params):
    """Make a GET request to the ListenBrainz API.

    Returns the parsed JSON along with an error message if the API responded
    with an error.
    """
    request = requests.get(f"{api_url}{path}", params=params)

    try:
        data = request.json()
    except JSONDecodeError:
        # Raise an exception if the HTTP request returned an error
        request.raise_for_status()

        # If raise_for_status() doesn't raise an exception, just re-raised the
        # existing error
        raise

    if isinstance(data, dict) and data.get("error"):
        return data, f"ListenBrainz error: {data['error']}."

    return data, None


def _track_info(track) -> str:
    """Format a ListenBrainz track entry into the "by artist from the album" tail."""
    meta = track.get("track_metadata", {})
    out = ""
    artist = meta.get("artist_name")
    if artist:
        out += f" by \x02{artist}\x0f"
    album = meta.get("release_name")
    if album:
        out += f" from the album \x02{album}\x0f"
    return out


@hook.command("listenbrainz", "lb", autohelp=False)
def listenbrainz(event, db, text, nick, bot):
    """[user] [dontsave] - displays the now playing (or last played) track of ListenBrainz user [user]"""
    # check if the user asked us not to save his details
    dontsave = text.endswith(" dontsave")
    if dontsave:
        user = text[:-9].strip().lower()
    else:
        user = text.strip().lower()

    if not user:
        user = get_account(nick)
        if not user:
            event.notice_doc()
            return None

    # playing-now returns the current event while the user is playing; if it
    # has no event (not playing, or a playing state with no event data) we
    # fall back to the history endpoint for the most recent listen.
    data, err = api_request(f"/user/{user}/playing-now", limit=1)
    if err:
        return err

    payload = data.get("payload", {})
    if not payload.get("listens"):
        data, err = api_request(f"/user/{user}/listens", limit=1)
        if err:
            return err
        payload = data.get("payload", {})

    listens = payload.get("listens") or []
    if not listens:
        return f'No recent tracks for user "{format_user(user)}" found.'

    listen = listens[0]

    if payload.get("playing_now"):
        # if the user is currently playing something, they are listening to it now
        status = "is listening to"
        ending = "."
    else:
        status = "last listened to"
        # otherwise, the user is not listening to anything right now
        # lets see how long ago they listened to it
        time_listened = datetime.fromtimestamp(listen["listened_at"])
        time_since = timeformat.time_since(time_listened)
        ending = f" ({time_since} ago)"

    title = listen.get("track_metadata", {}).get("track_name")
    out = f'{format_user(user)} {status}'
    if title:
        out += f' "{title}"'
    out += _track_info(listen)
    out += ending

    # save the username so the user does not have to pass it next time
    if text and not dontsave:
        if listen_cache.get(nick.lower()):
            db.execute(
                table.update()
                .values(acc=user)
                .where(table.c.nick == nick.lower())
            )
        else:
            db.execute(table.insert().values(nick=nick.lower(), acc=user))

        db.commit()
        load_cache(db)
    return out
