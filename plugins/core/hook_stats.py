"""
Tracks successful and errored launches of all hooks, allowing users to query the stats

Author:
    - linuxdaemon <https://github.com/linuxdaemon>
"""

from collections import defaultdict
from typing import Callable, Dict, List, Tuple

from cloudbot import hook
from cloudbot.hook import Priority
from cloudbot.util import web
from cloudbot.util.formatting import gen_markdown_table


def default_hook_counter():
    return {"success": 0, "failure": 0}


def hook_sorter(n):
    def _sorter(data):
        return sum(data[n].values())

    return _sorter


def get_stats(bot):
    try:
        stats = bot.memory["hook_stats"]
    except LookupError:
        bot.memory["hook_stats"] = stats = {
            "global": defaultdict(default_hook_counter),
            "network": defaultdict(lambda: defaultdict(default_hook_counter)),
            "channel": defaultdict(
                lambda: defaultdict(lambda: defaultdict(default_hook_counter))
            ),
        }

    return stats


@hook.post_hook(priority=Priority.HIGHEST)
def stats_sieve(launched_event, error, bot, launched_hook):
    chan = launched_event.chan
    conn = launched_event.conn
    status = "success" if error is None else "failure"
    stats = get_stats(bot)
    name = launched_hook.plugin.title + "." + launched_hook.function_name
    stats["global"][name][status] += 1
    if conn:
        stats["network"][conn.name.casefold()][name][status] += 1

        if chan:
            stats["channel"][conn.name.casefold()][chan.casefold()][name][
                status
            ] += 1


def do_basic_stats(data):
    table = [
        (hook_name, str(count["success"]), str(count["failure"]))
        for hook_name, count in sorted(
            data.items(), key=hook_sorter(1), reverse=True
        )
    ]
    return ("Hook", "Uses - Success", "Uses - Errored"), table


def do_global_stats(data):
    return do_basic_stats(data["global"])


def do_network_stats(data, network):
    return do_basic_stats(data["network"][network.casefold()])


def do_channel_stats(data, network, channel):
    return do_basic_stats(
        data["channel"][network.casefold()][channel.casefold()]
    )


def do_hook_stats(data, hook_name):
    table = [
        (net, chan, hooks[hook_name])
        for net, chans in data["channel"].items()
        for chan, hooks in chans.items()
    ]
    return ("Network", "Channel", "Uses - Success", "Uses - Errored"), [
        (net, chan, str(count["success"]), str(count["failure"]))
        for net, chan, count in sorted(table, key=hook_sorter(2), reverse=True)
    ]


Handler = Callable[..., Tuple[Tuple[str, ...], List[Tuple[str, ...]]]]
stats_funcs: Dict[str, Tuple[Handler, int]] = {
    "global": (do_global_stats, 0),
    "network": (do_network_stats, 1),
    "channel": (do_channel_stats, 2),
    "hook": (do_hook_stats, 1),
}


@hook.command(permissions=["snoonetstaff", "botcontrol"])
def hookstats(text, bot, notice_doc):
    """{global|network <name>|channel <network> <channel>|hook <hook>} - Get hook usage statistics"""
    args = text.split()
    stats_type = args.pop(0).lower()

    data = get_stats(bot)

    try:
        handler, arg_count = stats_funcs[stats_type]
    except LookupError:
        notice_doc()
        return None

    if len(args) < arg_count:
        notice_doc()
        return None

    headers, data = handler(data, *args[:arg_count])

    if not data:
        return "No stats available."

    table = gen_markdown_table(headers, data)

    return web.paste(table, "md", "hastebin")
