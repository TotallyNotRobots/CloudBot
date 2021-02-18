from datetime import datetime

import sqlalchemy
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    not_,
)
from sqlalchemy.sql import select

from cloudbot import hook
from cloudbot.util import database

table = Table(
    "notes",
    database.metadata,
    Column("note_id", Integer),
    Column("connection", String),
    Column("user", String),
    Column("text", String),
    Column("priority", Integer),
    Column("deleted", Boolean),
    Column("added", DateTime),
    PrimaryKeyConstraint("note_id", "connection", "user"),
)


def read_all_notes(db, server, user, show_deleted=False):
    if show_deleted:
        query = (
            select([table.c.note_id, table.c.text, table.c.added])
            .where(table.c.connection == server)
            .where(table.c.user == user.lower())
            .order_by(table.c.added)
        )
    else:
        query = (
            select([table.c.note_id, table.c.text, table.c.added])
            .where(table.c.connection == server)
            .where(table.c.user == user.lower())
            .where(not_(table.c.deleted))
            .order_by(table.c.added)
        )
    return db.execute(query).fetchall()


def delete_all_notes(db, server, user):
    query = (
        table.update()
        .where(table.c.connection == server)
        .where(table.c.user == user.lower())
        .values(deleted=True)
    )
    db.execute(query)
    db.commit()


def read_note(db, server, user, note_id):
    query = (
        select([table.c.note_id, table.c.text, table.c.added])
        .where(table.c.connection == server)
        .where(table.c.user == user.lower())
        .where(table.c.note_id == note_id)
    )
    return db.execute(query).fetchone()


def delete_note(db, server, user, note_id):
    query = (
        table.update()
        .where(table.c.connection == server)
        .where(table.c.user == user.lower())
        .where(table.c.note_id == note_id)
        .values(deleted=True)
    )
    db.execute(query)
    db.commit()


def add_note(db, server, user, text):
    id_query = select(
        [sqlalchemy.sql.expression.func.max(table.c.note_id).label("maxid")]
    ).where(table.c.user == user.lower())
    max_id = db.execute(id_query).scalar()

    if max_id is None:
        note_id = 1
    else:
        note_id = max_id + 1

    query = table.insert().values(
        note_id=note_id,
        connection=server,
        user=user.lower(),
        text=text,
        deleted=False,
        added=datetime.today(),
    )
    db.execute(query)
    db.commit()


def format_note(data):
    note_id, note_text, added = data

    # format timestamp
    added_string = added.strftime("%d %b, %Y")

    return "\x02Note #{}:\x02 {} - \x02{}\x02".format(
        note_id, note_text, added_string
    )


@hook.command("note", "notes", "todo")
def note(text, conn, nick, db, notice):
    """<add|list|get|del|clear> args - manipulates your list of notes"""
    parts = text.split()

    if len(parts) == 1 and text.isdigit():
        cmd = "get"
        args = parts
    else:
        cmd = parts[0].lower()
        args = parts[1:]

    if cmd in ["add", "new"]:
        # user is adding a note
        if not args:
            return "No text provided!"

        note_text = " ".join(args)

        # add note to database
        add_note(db, conn.name, nick, note_text)

        notice("Note added!")
        return

    if cmd in ["del", "delete", "remove"]:
        # user is deleting a note
        if not args:
            return "No note ID provided!"

        # but lets get the note first
        note_id = args[0]
        n = read_note(db, conn.name, nick, note_id)

        if not n:
            notice("#{} is not a valid note ID.".format(note_id))
            return

        # now we delete it
        delete_note(db, conn.name, nick, note_id)

        notice("Note #{} deleted!".format(note_id))
        return

    if cmd == "clear":
        # user is deleting all notes
        delete_all_notes(db, conn.name, nick)

        notice("All notes deleted!")
        return

    if cmd == "get":
        # user is getting a single note
        if not args:
            return "No note ID provided!"

        note_id = args[0]
        n = read_note(db, conn.name, nick, note_id)

        if not n:
            notice("{} is not a valid note ID.".format(nick))
            return

        # show the note
        text = format_note(n)
        notice(text)
        return

    if cmd in ["share", "show"]:
        # user is sharing a single note
        if not args:
            return "No note ID provided!"

        note_id = args[0]
        n = read_note(db, conn.name, nick, note_id)

        if not n:
            notice("{} is not a valid note ID.".format(nick))
            return

        # show the note
        text = format_note(n)
        return text

    if cmd == "list":
        # user is getting all notes
        notes = read_all_notes(db, conn.name, nick)

        if not notes:
            notice("You have no notes.")
            return

        notice("All notes for {}:".format(nick))

        for n in notes:
            # show the note
            text = format_note(n)
            notice(text)
    elif cmd == "listall":
        # user is getting all notes including deleted ones
        notes = read_all_notes(db, conn.name, nick, show_deleted=True)

        if not notes:
            notice("You have no notes.")
            return

        notice("All notes for {}:".format(nick))

        for n in notes:
            # show the note
            text = format_note(n)
            notice(text)
    else:
        notice("Unknown command: {}".format(cmd))
