from typing import Any

from cloudbot import hook
from cloudbot.hook import HookType, Priority
from cloudbot.plugin_hooks import CommandHook, Hook


@hook.sieve(priority=Priority.LOWEST)
def cmd_autohelp(bot, event, _hook: Hook[Any]):  # pyright: ignore[reportUnusedParameter]  # noqa: ARG001
    if (
        isinstance(_hook, CommandHook)
        and _hook.auto_help
        and not event.text
        and _hook.doc is not None
    ):
        event.notice_doc()
        return None

    return event


@hook.post_hook(priority=Priority.LOWEST)
def do_reply(result, error, launched_event, launched_hook) -> None:
    if launched_hook.type in (
        HookType.SIEVE,
        HookType.ON_START,
        HookType.ON_STOP,
    ):
        return

    if error is None and result is not None:
        if isinstance(result, (list, tuple)):
            # if there are multiple items in the response, return them on multiple lines
            launched_event.reply(*result)
        else:
            launched_event.reply(result)
