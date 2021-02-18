from cloudbot import hook
from cloudbot.hook import Priority


@hook.sieve(priority=Priority.LOWEST)
def cmd_autohelp(bot, event, _hook):
    if (
        _hook.type == "command"
        and _hook.auto_help
        and not event.text
        and _hook.doc is not None
    ):
        event.notice_doc()
        return None

    return event


@hook.post_hook(priority=Priority.LOWEST)
def do_reply(result, error, launched_event, launched_hook):
    if launched_hook.type in ("sieve", "on_start", "on_stop"):
        return

    if error is None and result is not None:
        if isinstance(result, (list, tuple)):
            # if there are multiple items in the response, return them on multiple lines
            launched_event.reply(*result)
        else:
            launched_event.reply(result)
