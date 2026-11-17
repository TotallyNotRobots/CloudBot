from __future__ import annotations

from operator import attrgetter
from typing import TYPE_CHECKING

from cloudbot import hook
from cloudbot.util import formatting, web

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot
    from cloudbot.client import Client
    from cloudbot.event_functions import (
        EventHasPermission,
        EventMessage,
        EventNotice,
    )


def get_potential_commands(bot, cmd_name):
    cmd_name = cmd_name.lower().strip()
    try:
        yield cmd_name, bot.plugin_manager.commands[cmd_name]
    except LookupError:
        for name, _hook in bot.plugin_manager.commands.items():
            if name.startswith(cmd_name):
                yield name, _hook


@hook.command("help", autohelp=False)
def help_command(
    text: str,
    chan: str,
    bot: CloudBot,
    notice: EventNotice,
    message: EventMessage,
    has_permission: EventHasPermission,
    triggered_prefix: str,
) -> None:
    """[command] - gives help for [command], or lists all available commands if no command is specified"""
    if text:
        searching_for = text.lower().strip()
    else:
        searching_for = None

    if text:
        cmds = list(get_potential_commands(bot, text))
        if not cmds:
            notice(f"Unknown command '{text}'")
            return

        if len(cmds) > 1:
            notice(
                f"Possible matches: {formatting.get_text_list(sorted([command for command, _ in cmds]))}"
            )
            return

        doc = cmds[0][1].doc

        if doc:
            notice(f"{triggered_prefix}{searching_for} {doc}")
        else:
            notice(f"Command {searching_for} has no additional documentation.")
    else:
        commands = []

        for plugin in sorted(
            set(bot.plugin_manager.commands.values()), key=attrgetter("name")
        ):
            # use set to remove duplicate commands (from multiple aliases), and sorted to sort by name

            if plugin.permissions:
                # check permissions
                allowed = False
                for perm in plugin.permissions:
                    if has_permission(perm, notice=False):
                        allowed = True
                        break

                if not allowed:
                    # skip adding this command
                    continue

            # add the command to lines sent
            command = plugin.name

            commands.append(command)

        # list of lines to send to the user
        lines = formatting.chunk_str(
            f"Here's a list of commands you can use: {', '.join(commands)}"
        )

        for line in lines:
            if chan[:1] == "#":
                notice(line)
            else:
                # This is an user in this case.
                message(line)

        notice(
            f"For detailed help, use {triggered_prefix}help <command>, without the brackets."
        )


@hook.command()
async def cmdinfo(text: str, bot: CloudBot, notice: EventNotice) -> None:
    """<command> - Gets various information about a command"""
    name = text.split(maxsplit=1)[0]
    cmds = list(get_potential_commands(bot, name))
    if not cmds:
        notice(f"Unknown command: '{name}'")
        return

    if len(cmds) > 1:
        notice(
            f"Possible matches: {formatting.get_text_list(sorted([command for command, plugin in cmds]))}"
        )
        return

    cmd_hook = cmds[0][1]

    hook_name = f"{cmd_hook.plugin.title}.{cmd_hook.function_name}"
    info = f"Command: {cmd_hook.name}, Aliases: [{', '.join(cmd_hook.aliases)}], Hook name: {hook_name}"

    if cmd_hook.permissions:
        info += f", Permissions: [{', '.join(cmd_hook.permissions)}]"

    notice(info)


@hook.command(permissions=["botcontrol"], autohelp=False)
def generatehelp(conn: Client, bot):
    """- Dumps a list of commands with their help text to the docs directory formatted using markdown."""
    message = f"{conn.nick} Command list\n"
    message += "------\n"
    for plugin in sorted(
        set(bot.plugin_manager.commands.values()), key=attrgetter("name")
    ):
        # use set to remove duplicate commands (from multiple aliases), and sorted to sort by name
        command = plugin.name
        doc = bot.plugin_manager.commands[command].doc
        permission = ", ".join(plugin.permissions)
        aliases = ", ".join(
            alias for alias in plugin.aliases if alias != command
        )
        if doc:
            doc = (
                doc.replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("[", "&lt;")
                .replace("]", "&gt;")
            )
            if aliases:
                message += f"**{command} ({aliases}):** {doc}\n\n"
            else:
                # No aliases so just print the commands
                message += f"**{command}**: {doc}\n\n"
        else:
            message += f"**{command}**: Command has no documentation.\n\n"
        if permission:
            message = message[:-2]
            message += f" ( *Permission required:* {permission})\n\n"
    # toss the markdown text into a paste
    return web.paste(message)
