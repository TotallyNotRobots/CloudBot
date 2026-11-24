from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, final

from sqlalchemy import delete
from sqlalchemy.orm import Mapped, Session, mapped_column

from cloudbot import hook
from cloudbot.event import CommandEvent
from cloudbot.util import database
from cloudbot.util.formatting import chunk_str, pluralize_auto

if TYPE_CHECKING:
    from cloudbot.event_functions import EventNoticeDoc


@final
class Commands(database.Base):
    __tablename__ = "chain_commands_v2"

    hook: Mapped[str] = mapped_column(primary_key=True)
    allowed: Mapped[bool] = mapped_column(default=True)


allow_cache: dict[str, bool] = {}


@hook.on_start()
def load_cache(db: Session) -> None:
    new_cache: dict[str, bool] = {}
    for row in db.query(Commands).all():
        new_cache[row.hook] = row.allowed

    allow_cache.clear()
    allow_cache.update(new_cache)


def format_hook_name(_hook) -> str:
    return f"{_hook.plugin.title}.{_hook.function.__name__}"


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


def handle_chainallow_add(
    args: list[str], notice_doc: EventNoticeDoc, hook_name: str, db: Session
) -> str | None:
    item = Commands(hook=hook_name)
    if args:
        allow = args.pop(0).lower()
        if allow == "allow":
            item.allowed = True
        elif allow == "deny":
            item.allowed = False
        else:
            return notice_doc()

    updated = hook_name in allow_cache
    item = db.merge(item)

    db.commit()
    load_cache(db)
    if updated:
        return f"Updated state of '{hook_name}' in chainallow to allowed={allow_cache.get(hook_name)}"

    if allow_cache.get(hook_name):
        return f"Added '{hook_name}' as an allowed command"

    return f"Added '{hook_name}' as a denied command"


def handle_chainallow_del(args, notice_doc, hook_name: str, db: Session) -> str:  # pyright: ignore[reportUnusedParameter]  # noqa: ARG001
    condition = Commands.hook == hook_name
    items = db.query(Commands).filter(condition).all()
    count = len(items)
    db.execute(delete(Commands).where(condition))
    db.commit()
    load_cache(db)
    return f"Deleted {pluralize_auto(count, 'row')}."


chainallow_subcmds = {
    "add": handle_chainallow_add,
    "del": handle_chainallow_del,
}


@hook.command(permissions=["botcontrol", "snoonetstaff"])
def chainallow(text, db, notice_doc: EventNoticeDoc, bot):
    """{add [hook] [{allow|deny}]|del [hook]} - Manage the allowed list of commands for the chain command"""
    args = text.split()
    subcmd = args.pop(0).lower()

    if not args or subcmd not in chainallow_subcmds:
        return notice_doc()

    name = args.pop(0)
    _hook = get_hook_from_command(bot, name)
    if _hook is None:
        return f"Unable to find command '{name}'"

    hook_name = format_hook_name(_hook)

    return chainallow_subcmds[subcmd](args, notice_doc, hook_name, db)


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
    return CommandEvent(
        base_event=event,
        text=args.strip(),
        triggered_command=cmd,
        hook=_hook,
        cmd_prefix="",
    )


@hook.command()
async def chain(text, bot, event):
    """<cmd1> [args...] | <cmd2> [args...] | ... - Runs commands in a chain, piping the output from previous commands
    to the next"""
    cmds = parse_chain(text, bot)

    for name, _hook, _ in cmds:
        if _hook is None:
            return f"Unable to find command '{name}'"

        if not is_hook_allowed(_hook):
            event.notice(
                f"'{format_hook_name(_hook)}' may not be used in command piping"
            )
            return None

        if _hook.permissions:
            allowed = await event.check_permissions(_hook.permissions)
            if not allowed:
                event.notice(
                    f"Sorry, you are not allowed to use '{format_hook_name(_hook)}'."
                )
                return None

    buffer = ""

    out_func = None
    _target = None

    def message(msg, target=None) -> None:
        nonlocal buffer
        nonlocal out_func
        nonlocal _target
        buffer += (" " if buffer else "") + msg
        if out_func is None:
            out_func = event.message

        _target = target

    def reply(*messages, target=None) -> None:
        nonlocal buffer
        nonlocal out_func
        nonlocal _target
        buffer += (" " if buffer else "") + " ".join(messages)
        if out_func is None:
            out_func = event.reply

        _target = target

    def action(msg, target=None) -> None:
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

    return None


@hook.command(autohelp=False)
def chainlist(bot, event) -> None:
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
