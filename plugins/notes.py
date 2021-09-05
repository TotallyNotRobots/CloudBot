"""
Notes/todo list
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    and_,
    func,
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


def where_user(server, user):
    """Generate a whereclause to match a user"""
    return and_(
        table.c.connection == server.lower(),
        table.c.user == user.lower(),
    )


def read_all_notes(db, server, user, show_deleted=False):
    query = select([table.c.note_id, table.c.text, table.c.added]).where(
        where_user(server, user)
    )

    if not show_deleted:
        query = query.where(not_(table.c.deleted))

    query = query.order_by(table.c.added)
    return db.execute(query).fetchall()


def delete_all_notes(db, server, user):
    query = table.update().where(where_user(server, user)).values(deleted=True)

    db.execute(query)
    db.commit()


def read_note(db, server, user, note_id):
    query = (
        select([table.c.note_id, table.c.text, table.c.added])
        .where(where_user(server, user))
        .where(table.c.note_id == note_id)
    )
    return db.execute(query).fetchone()


def delete_note(db, server, user, note_id):
    query = (
        table.update()
        .where(where_user(server, user))
        .where(table.c.note_id == note_id)
        .values(deleted=True)
    )
    db.execute(query)
    db.commit()


def add_note(db, server, user, text):
    id_query = select([func.max(table.c.note_id).label("maxid")]).where(
        where_user(server, user)
    )
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
def note(text, db, event):
    """<add|list|get|del|clear> args - manipulates your list of notes"""
    notice = event.notice
    args, cmd = parse_args(text)

    if cmd in ["add", "new"]:
        return cmd_add(args, db, event)

    if cmd in ["del", "delete", "remove"]:
        return cmd_del(args, db, event)

    if cmd == "clear":
        cmd_clear(db, event)
        return None

    if cmd == "get":
        return cmd_get(args, db, event)

    if cmd in ["share", "show"]:
        return cmd_show(args, db, event)

    if cmd == "list":
        return cmd_list(db, event)

    if cmd == "listall":
        return cmd_listall(db, event)

    notice("Unknown command: {}".format(cmd))
    return None


def parse_args(text):
    parts = text.split()
    if len(parts) == 1 and text.isdigit():
        cmd = "get"
        args = parts
    else:
        cmd = parts[0].lower()
        args = parts[1:]
    return args, cmd


def cmd_clear(db, event):
    # user is deleting all notes
    delete_all_notes(db, event.conn.name, event.nick)
    event.notice("All notes deleted!")


def cmd_listall(db, event):
    # user is getting all notes including deleted ones
    notes = read_all_notes(db, event.conn.name, event.nick, show_deleted=True)
    if not notes:
        event.notice("You have no notes.")
        return None

    event.notice("All notes for {}:".format(event.nick))
    for n in notes:
        # show the note
        text = format_note(n)
        event.notice(text)

    return None


def cmd_list(db, event):
    # user is getting all notes
    notes = read_all_notes(db, event.conn.name, event.nick)
    if not notes:
        event.notice("You have no notes.")
        return None

    event.notice("All notes for {}:".format(event.nick))
    for n in notes:
        # show the note
        text = format_note(n)
        event.notice(text)

    return None


def cmd_show(args, db, event):
    # user is sharing a single note
    if not args:
        event.notice("No note ID provided!")
        return None

    note_id = args[0]
    n = read_note(db, event.conn.name, event.nick, note_id)
    if not n:
        event.notice("{} is not a valid note ID.".format(note_id))
        return None

    # show the note
    text = format_note(n)
    return text


def cmd_get(args, db, event):
    # user is getting a single note
    # show the note
    text = cmd_show(args, db, event)
    if text is not None:
        event.notice(text)


def cmd_del(args, db, event):
    # user is deleting a note
    if not args:
        return "No note ID provided!"

    # but lets get the note first
    note_id = args[0]
    n = read_note(db, event.conn.name, event.nick, note_id)
    if not n:
        event.notice("#{} is not a valid note ID.".format(note_id))
        return None

    # now we delete it
    delete_note(db, event.conn.name, event.nick, note_id)
    event.notice("Note #{} deleted!".format(note_id))
    return None


def cmd_add(args, db, event):
    """user is adding a note"""
    if not args:
        return "No text provided!"

    note_text = " ".join(args)
    # add note to database
    add_note(db, event.conn.name, event.nick, note_text)
    event.notice("Note added!")
    return None
