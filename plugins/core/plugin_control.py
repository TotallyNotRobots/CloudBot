import asyncio
from operator import itemgetter
from pathlib import Path

from cloudbot import hook
from cloudbot.util import web


def gen_markdown_table(headers, rows):
    rows = list(rows)
    rows.insert(0, headers)
    rotated = zip(*reversed(rows))

    sizes = tuple(map(lambda l: max(map(len, l)), rotated))
    rows.insert(1, tuple(('-' * size) for size in sizes))
    lines = [
        "| {} |".format(' | '.join(cell.ljust(sizes[i]) for i, cell in enumerate(row)))
        for row in rows
    ]
    return '\n'.join(lines)


@hook.command(permissions=["botcontrol"], autohelp=False)
def pluginlist(bot):
    """- List all currently loaded plugins"""
    manager = bot.plugin_manager
    plugins = [
        (plugin.title, str(Path(plugin.file_path).resolve().relative_to(bot.base_dir)))
        for plugin in manager.plugins.values()
    ]
    plugins.sort(key=itemgetter(0))
    table = gen_markdown_table(["Plugin", "Path"], plugins)
    return web.paste(table, service="hastebin")


@asyncio.coroutine
@hook.command(permissions=["botcontrol"])
def pluginload(bot, text, reply):
    """<plugin path> - (Re)load <plugin> manually"""
    manager = bot.plugin_manager
    path = str(Path(text.strip()).resolve())
    was_loaded = path in manager.plugins
    coro = bot.plugin_manager.load_plugin(path)

    try:
        yield from coro
    except Exception:
        reply("Plugin failed to load.")
        raise
    else:
        return "Plugin {}loaded successfully.".format("re" if was_loaded else "")


@asyncio.coroutine
@hook.command(permissions=["botcontrol"])
def pluginunload(bot, text):
    """<plugin path> - Unload <plugin> manually"""
    manager = bot.plugin_manager
    path = str(Path(text.strip()).resolve())
    is_loaded = path in manager.plugins

    if not is_loaded:
        return "Plugin not loaded, unable to unload."

    if (yield from manager.unload_plugin(path)):
        return "Plugin unloaded successfully."

    return "Plugin failed to unload."
