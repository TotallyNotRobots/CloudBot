from operator import attrgetter

from cloudbot import hook
from cloudbot.util import formatting, web


def get_potential_commands(bot, cmd_name):
    cmd_name = cmd_name.lower().strip()
    try:
        yield cmd_name, bot.plugin_manager.commands[cmd_name]
    except LookupError:
        for name, _hook in bot.plugin_manager.commands.items():
            if name.startswith(cmd_name):
                yield name, _hook


@hook.command("help", autohelp=False)
async def help_command(
    text, chan, bot, notice, message, has_permission, triggered_prefix
):
    """[command] - gives help for [command], or lists all available commands if no command is specified"""
    if text:
        searching_for = text.lower().strip()
    else:
        searching_for = None

    if text:
        cmds = list(get_potential_commands(bot, text))
        if not cmds:
            notice("Unknown command '{}'".format(text))
            return

        if len(cmds) > 1:
            notice(
                "Possible matches: {}".format(
                    formatting.get_text_list(
                        sorted([command for command, _ in cmds])
                    )
                )
            )
            return

        doc = cmds[0][1].doc

        if doc:
            notice("{}{} {}".format(triggered_prefix, searching_for, doc))
        else:
            notice(
                "Command {} has no additional documentation.".format(
                    searching_for
                )
            )
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
            "Here's a list of commands you can use: " + ", ".join(commands)
        )

        for line in lines:
            if chan[:1] == "#":
                notice(line)
            else:
                # This is an user in this case.
                message(line)

        notice(
            "For detailed help, use {}help <command>, without the brackets.".format(
                triggered_prefix
            )
        )


@hook.command()
async def cmdinfo(text, bot, notice):
    """<command> - Gets various information about a command"""
    name = text.split()[0]
    cmds = list(get_potential_commands(bot, name))
    if not cmds:
        notice("Unknown command: '{}'".format(name))
        return

    if len(cmds) > 1:
        notice(
            "Possible matches: {}".format(
                formatting.get_text_list(
                    sorted([command for command, plugin in cmds])
                )
            )
        )
        return

    cmd_hook = cmds[0][1]

    hook_name = cmd_hook.plugin.title + "." + cmd_hook.function_name
    info = "Command: {}, Aliases: [{}], Hook name: {}".format(
        cmd_hook.name, ", ".join(cmd_hook.aliases), hook_name
    )

    if cmd_hook.permissions:
        info += ", Permissions: [{}]".format(", ".join(cmd_hook.permissions))

    notice(info)


@hook.command(permissions=["botcontrol"], autohelp=False)
def generatehelp(conn, bot):
    """- Dumps a list of commands with their help text to the docs directory formatted using markdown."""
    message = "{} Command list\n".format(conn.nick)
    message += "------\n"
    for plugin in sorted(
        set(bot.plugin_manager.commands.values()), key=attrgetter("name")
    ):
        # use set to remove duplicate commands (from multiple aliases), and sorted to sort by name
        command = plugin.name
        aliases = ""
        doc = bot.plugin_manager.commands[command].doc
        permission = ""
        for perm in plugin.permissions:
            permission += perm + ", "
        permission = permission[:-2]
        for alias in plugin.aliases:
            if alias == command:
                pass
            else:
                aliases += alias + ", "
        aliases = aliases[:-2]
        if doc:
            doc = (
                doc.replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("[", "&lt;")
                .replace("]", "&gt;")
            )
            if aliases:
                message += "**{} ({}):** {}\n\n".format(command, aliases, doc)
            else:
                # No aliases so just print the commands
                message += "**{}**: {}\n\n".format(command, doc)
        else:
            message += "**{}**: Command has no documentation.\n\n".format(
                command
            )
        if permission:
            message = message[:-2]
            message += " ( *Permission required:* {})\n\n".format(permission)
    # toss the markdown text into a paste
    return web.paste(message)
