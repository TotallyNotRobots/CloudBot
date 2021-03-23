import itertools
from typing import Dict

from sqlalchemy import Boolean, Column, PrimaryKeyConstraint, String, Table

from cloudbot import hook
from cloudbot.event import CommandEvent
from cloudbot.util import database
from cloudbot.util.formatting import chunk_str, pluralize_auto

commands = Table(
    "chain_commands",
    database.metadata,
    Column("hook", String),
    Column("allowed", Boolean, default=True),
    PrimaryKeyConstraint("hook", "allowed"),
)

allow_cache: Dict[str, bool] = {}


@hook.on_start()
def load_cache(db):
    new_cache = {}
    for row in db.execute(commands.select()):
        new_cache[row["hook"]] = row["allowed"]

    allow_cache.clear()
    allow_cache.update(new_cache)


def format_hook_name(_hook):
    return _hook.plugin.title + "." + _hook.function.__name__


def get_hook_from_command(bot, hook_name):
    manager = bot.plugin_manager
    if "." in hook_name:
        for _hook in manager.commands.values():
            if format_hook_name(_hook) == hook_name:
                return _hook

        return None

    try:
        _hook = manager.commands[hook_name]
    except LookupError:
        pass
    else:
        return _hook

    possible = []
    for name, _hook in manager.commands.items():
        if name.startswith(hook_name):
            possible.append(_hook)

    return possible[0] if len(possible) == 1 else None


@hook.command(permissions=["botcontrol", "snoonetstaff"])
def chainallow(text, db, notice_doc, bot):
    """{add [hook] [{allow|deny}]|del [hook]} - Manage the allowed list fo comands for the chain command"""
    args = text.split()
    subcmd = args.pop(0).lower()

    if not args:
        return notice_doc()

    name = args.pop(0)
    _hook = get_hook_from_command(bot, name)
    if _hook is None:
        return "Unable to find command '{}'".format(name)

    hook_name = format_hook_name(_hook)

    if subcmd == "add":
        values = {"hook": hook_name}
        if args:
            allow = args.pop(0).lower()
            if allow == "allow":
                allow = True
            elif allow == "deny":
                allow = False
            else:
                return notice_doc()

            values["allowed"] = allow

        updated = True
        res = db.execute(
            commands.update()
            .values(**values)
            .where(commands.c.hook == hook_name)
        )
        if res.rowcount == 0:
            updated = False
            db.execute(commands.insert().values(**values))

        db.commit()
        load_cache(db)
        if updated:
            return "Updated state of '{}' in chainallow to allowed={}".format(
                hook_name, allow_cache.get(hook_name)
            )

        if allow_cache.get(hook_name):
            return "Added '{}' as an allowed command".format(hook_name)

        return "Added '{}' as a denied command".format(hook_name)

    if subcmd == "del":
        res = db.execute(commands.delete().where(commands.c.hook == hook_name))
        db.commit()
        load_cache(db)
        return "Deleted {}.".format(pluralize_auto(res.rowcount, "row"))

    return notice_doc()


def parse_chain(text, bot):
    parts = text.split("|")
    cmds = []

    for part in parts:
        cmd, _, args = part.strip().partition(" ")
        _hook = get_hook_from_command(bot, cmd)
        cmds.append([cmd, _hook, args or ""])

    return cmds


def is_hook_allowed(_hook):
    name = format_hook_name(_hook)
    return bool(allow_cache.get(name))


def wrap_event(_hook, event, cmd, args):
    cmd_event = CommandEvent(
        base_event=event,
        text=args.strip(),
        triggered_command=cmd,
        hook=_hook,
        cmd_prefix="",
    )
    return cmd_event


@hook.command()
async def chain(text, bot, event):
    """<cmd1> [args...] | <cmd2> [args...] | ... - Runs commands in a chain, piping the output from previous commands
    to tne next"""
    cmds = parse_chain(text, bot)

    for name, _hook, _ in cmds:
        if _hook is None:
            return "Unable to find command '{}'".format(name)

        if not is_hook_allowed(_hook):
            event.notice(
                "'{}' may not be used in command piping".format(
                    format_hook_name(_hook)
                )
            )
            return

        if _hook.permissions:
            allowed = await event.check_permissions(_hook.permissions)
            if not allowed:
                event.notice(
                    "Sorry, you are not allowed to use '{}'.".format(
                        format_hook_name(_hook)
                    )
                )
                return

    buffer = ""

    out_func = None
    _target = None

    def message(msg, target=None):
        nonlocal buffer
        nonlocal out_func
        nonlocal _target
        buffer += (" " if buffer else "") + msg
        if out_func is None:
            out_func = event.message

        _target = target

    def reply(*messages, target=None):
        nonlocal buffer
        nonlocal out_func
        nonlocal _target
        buffer += (" " if buffer else "") + " ".join(messages)
        if out_func is None:
            out_func = event.reply

        _target = target

    def action(msg, target=None):
        nonlocal buffer
        nonlocal out_func
        nonlocal _target
        buffer += (" " if buffer else "") + msg
        if out_func is None:
            out_func = event.action

        _target = target

    while cmds:
        cmd, _hook, args = cmds.pop(0)
        args += (" " if args else "") + buffer
        buffer = ""
        cmd_event = wrap_event(_hook, event, cmd, args)
        cmd_event.message = message
        cmd_event.reply = reply
        cmd_event.action = action
        if _hook.auto_help and not cmd_event.text and _hook.doc is not None:
            cmd_event.notice_doc()
            return "Invalid syntax."

        ok, res = await bot.plugin_manager.internal_launch(_hook, cmd_event)
        if not ok:
            return "Error occurred."

        if res:
            if out_func is None:
                out_func = event.reply

            buffer += (" " if buffer else "") + res

    if buffer:
        if out_func is None:
            out_func = event.reply

        out_func(buffer, target=_target)


@hook.command(autohelp=False)
def chainlist(bot, event):
    """- Returns the list of commands allowed in 'chain'"""
    hooks = [
        get_hook_from_command(bot, name)
        for name, allowed in allow_cache.items()
        if allowed
    ]
    s = ", ".join(
        sorted(
            itertools.chain.from_iterable(
                h.aliases for h in hooks if h is not None
            )
        )
    )

    for part in chunk_str(s):
        event.notice(part)
