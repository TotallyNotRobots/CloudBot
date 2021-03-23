import operator
import re
from collections import defaultdict
from typing import Dict

import sqlalchemy
from sqlalchemy import (
    Column,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    and_,
    select,
)
from sqlalchemy.sql.base import Executable

from cloudbot import hook
from cloudbot.util import database

karmaplus_re = re.compile(r"^.*\+\+$")
karmaminus_re = re.compile("^.*--$")

karma_table = Table(
    "karma",
    database.metadata,
    Column("name", String),
    Column("chan", String),
    Column("thing", String),
    Column("score", Integer),
    PrimaryKeyConstraint("name", "chan", "thing"),
)


@hook.on_start()
def remove_non_channel_points(db):
    """Temporary on_start hook to remove non-channel points"""
    db.execute(
        karma_table.delete().where(
            sqlalchemy.not_(karma_table.c.chan.startswith("#"))
        )
    )
    db.commit()


def update_score(nick, chan, thing, score, db):
    if nick.casefold() == chan.casefold():
        # This is a PM, don't set points in a PM
        return

    thing = thing.strip()
    clause = and_(
        karma_table.c.name == nick,
        karma_table.c.chan == chan,
        karma_table.c.thing == thing.lower(),
    )
    karma = db.execute(select([karma_table.c.score]).where(clause)).fetchone()
    query: Executable
    if karma:
        score += karma["score"]
        query = karma_table.update().values(score=score).where(clause)
    else:
        query = karma_table.insert().values(
            name=nick, chan=chan, thing=thing.lower(), score=score
        )

    db.execute(query)
    db.commit()


@hook.command("pp", "addpoint")
def addpoint(text, nick, chan, db):
    """<thing> - adds a point to the <thing>"""
    update_score(nick, chan, text, 1, db)


@hook.regex(karmaplus_re)
def re_addpt(match, nick, chan, db, notice):
    """no useful help txt"""
    thing = match.group().split("++")[0]
    if thing:
        addpoint(thing, nick, chan, db)
    else:
        notice(pluspts(nick, chan, db))


@hook.command("mm", "rmpoint")
def rmpoint(text, nick, chan, db):
    """<thing> - subtracts a point from the <thing>"""
    update_score(nick, chan, text, -1, db)


@hook.command("pluspts", autohelp=False)
def pluspts(nick, chan, db):
    """- prints the things you have liked and their scores"""
    output = ""
    clause = and_(
        karma_table.c.name == nick,
        karma_table.c.chan == chan,
        karma_table.c.score >= 0,
    )
    query = (
        select([karma_table.c.thing, karma_table.c.score])
        .where(clause)
        .order_by(karma_table.c.score.desc())
    )
    likes = db.execute(query).fetchall()

    for like in likes:
        output += "{} has {} points ".format(like[0], like[1])

    return output


@hook.command("minuspts", autohelp=False)
def minuspts(nick, chan, db):
    """- prints the things you have disliked and their scores"""
    output = ""
    clause = and_(
        karma_table.c.name == nick,
        karma_table.c.chan == chan,
        karma_table.c.score <= 0,
    )
    query = (
        select([karma_table.c.thing, karma_table.c.score])
        .where(clause)
        .order_by(karma_table.c.score)
    )
    likes = db.execute(query).fetchall()

    for like in likes:
        output += "{} has {} points ".format(like[0], like[1])

    return output


@hook.regex(karmaminus_re)
def re_rmpt(match, nick, chan, db, notice):
    """no useful help txt"""
    thing = match.group().split("--")[0]
    if thing:
        rmpoint(thing, nick, chan, db)
    else:
        notice(minuspts(nick, chan, db))


@hook.command("points", autohelp=False)
def points_cmd(text, chan, db):
    """<thing> - will print the total points for <thing> in the channel."""
    score = 0
    thing = ""
    if text.endswith(("-global", " global")):
        thing = text[:-7].strip()
        query = select([karma_table.c.score]).where(
            karma_table.c.thing == thing.lower()
        )
    else:
        text = text.strip()
        query = (
            select([karma_table.c.score])
            .where(karma_table.c.thing == text.lower())
            .where(karma_table.c.chan == chan)
        )

    karma = db.execute(query).fetchall()
    if karma:
        pos = 0
        neg = 0
        for k in karma:
            if int(k[0]) < 0:
                neg += int(k[0])
            else:
                pos += int(k[0])
            score += int(k[0])
        if thing:
            return "{} has a total score of {} (+{}/{}) across all channels I know about.".format(
                thing, score, pos, neg
            )
        return "{} has a total score of {} (+{}/{}) in {}.".format(
            text, score, pos, neg, chan
        )

    return "I couldn't find {} in the database.".format(text)


def parse_lookup(text, db, chan, name):
    if text in ("global", "-global"):
        items = db.execute(
            select([karma_table.c.thing, karma_table.c.score])
        ).fetchall()
        out = "The {{}} most {} things in all channels are: ".format(name)
    else:
        items = db.execute(
            select([karma_table.c.thing, karma_table.c.score]).where(
                karma_table.c.chan == chan
            )
        ).fetchall()
        out = "The {{}} most {} things in {{}} are: ".format(name)

    return out, items


def do_list(text, db, chan, loved=True):
    counts: Dict[str, int] = defaultdict(int)
    out, items = parse_lookup(text, db, chan, "loved" if loved else "hated")
    if not items:
        return None

    for item in items:
        thing = item[0]
        score = int(item[1])
        counts[thing] += score

    scores = counts.items()
    sorts = sorted(scores, key=operator.itemgetter(1), reverse=loved)[:10]
    out = out.format(len(sorts), chan) + " \u2022 ".join(
        "{} with {} points".format(thing[0], thing[1]) for thing in sorts
    )
    return out


@hook.command("topten", "pointstop", "loved", autohelp=False)
def pointstop(text, chan, db):
    """- prints the top 10 things with the highest points in the channel. To see the top 10 items in all of the
    channels the bot sits in use .topten global."""
    return do_list(text, db, chan)


@hook.command("bottomten", "pointsbottom", "hated", autohelp=False)
def pointsbottom(text, chan, db):
    """- prints the top 10 things with the lowest points in the channel. To see the bottom 10 items in all of the
    channels the bot sits in use .bottomten global."""
    return do_list(text, db, chan, False)
