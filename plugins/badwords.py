from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING, final

from sqlalchemy import delete, insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.util import database

if TYPE_CHECKING:
    from re import Pattern

    from cloudbot.clients.irc import IrcClient
    from cloudbot.event_functions import EventMessage


@final
class BadWord(database.Base):
    __tablename__ = "badwords"

    word: Mapped[str] = mapped_column(primary_key=True)
    nick: Mapped[str | None]
    chan: Mapped[str] = mapped_column(primary_key=True)


badcache: dict[str, list[str]] = defaultdict(list)


class BadwordMatcher:
    regex: Pattern[str] | None = None


matcher = BadwordMatcher()


@hook.on_start()
@hook.command("loadbad", permissions=["badwords"], autohelp=False)
def load_bad(db: Session) -> None:
    """- Should run on start of bot to load the existing words into the regex"""
    words: list[str] = []
    new_cache: defaultdict[str, list[str]] = defaultdict(list)
    for badword in db.query(BadWord).all():
        new_cache[badword.chan.casefold()].append(badword.word)
        words.append(badword.word)

    new_regex = re.compile(
        rf"(?:\s|^|[^\w\s])({'|'.join(words)})(?:\s|$|[^\w\s])", re.IGNORECASE
    )

    matcher.regex = new_regex

    badcache.clear()
    badcache.update(new_cache)


@hook.command("addbad", permissions=["badwords"])
def add_bad(text, nick, db: Session) -> str:
    """<word> <channel> - adds a bad word to the auto kick list must specify a channel with each word"""
    splt = text.lower().split(None, 1)
    word, channel = splt
    if not channel.startswith("#"):
        return "Please specify a valid channel name after the bad word."

    word = re.escape(word)
    wordlist = list_bad(channel)
    if word in wordlist:
        return f"{word} is already added to the bad word list for {channel}"

    if len(badcache[channel]) >= 10:
        return (
            f"There are too many words listed for channel {channel}. Please remove a word using .rmbad before adding "
            "anymore. For a list of bad words use .listbad"
        )

    db.execute(insert(BadWord).values(word=word, nick=nick, chan=channel))
    db.commit()
    load_bad(db)
    wordlist = list_bad(channel)
    return f"Current badwords: {wordlist}"


@hook.command("rmbad", "delbad", permissions=["badwords"])
def del_bad(text, db: Session) -> str:
    """<word> <channel> - removes the specified word from the specified channels bad word list"""
    splt = text.lower().split(None, 1)
    word, channel = splt
    if not channel.startswith("#"):
        return "Please specify a valid channel name after the bad word."

    db.execute(
        delete(BadWord)
        .where(BadWord.word == word)
        .where(BadWord.chan == channel)
    )
    db.commit()
    newlist = list_bad(channel)
    load_bad(db)
    return f"Removing {word} new bad word list for {channel} is: {newlist}"


@hook.command("listbad", permissions=["badwords"])
def list_bad(text):
    """<channel> - Returns a list of bad words specify a channel to see words for a particular channel"""
    text = text.split(" ")[0].lower()
    if not text.startswith("#"):
        return "Please specify a valid channel name"

    return "|".join(badcache[text])


@hook.event(
    [EventType.message, EventType.action], singlethread=True, clients=["irc"]
)
def check_badwords(
    conn: IrcClient, message: EventMessage, chan, content, nick
) -> None:
    if not matcher.regex:
        return

    match = matcher.regex.match(content)
    if not match:
        return

    # Check to see if the match is for this channel
    word = match.group().lower().strip()
    if word in badcache[chan]:
        conn.cmd("KICK", chan, nick, "that fucking word is so damn offensive")
        message(f"{nick}, congratulations you've won!")
