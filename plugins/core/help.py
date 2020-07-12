from operator import attrgetter

from cloudbot import hook
from cloudbot.bot import CloudBot
from cloudbot.event import CommandEvent
from cloudbot.util import formatting, web

DETAIL_HELP_MSG = (
    "For detailed help, use {}help <command>, without the brackets."
)

NO_HELP_MSG = "Command {} has no additional documentation."


def get_potential_commands(bot, cmd_name):
    """
    :type bot: cloudbot.bot.CloudBot
    :type cmd_name: str
    """
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
    event: CommandEvent,
    triggered_prefix: str,
) -> None:
    """
    [command] - gives help for [command], or lists all available commands
    if no command is specified
    """
    if text:
        searching_for = text.lower().strip()
    else:
        searching_for = None

    if text:
        cmds = list(get_potential_commands(bot, text))
        if not cmds:
            event.notice("Unknown command '{}'".format(text))
            return

        if len(cmds) > 1:
            commands = sorted([command for command, _ in cmds])
            event.notice(
                "Possible matches: {}".format(
                    formatting.get_text_list(commands)
                )
            )
            return

        doc = cmds[0][1].doc

        if doc:
            event.notice("{}{} {}".format(triggered_prefix, searching_for, doc))
        else:
            event.notice(NO_HELP_MSG.format(searching_for))
    else:
        commands = []

        for plugin in sorted(
            set(bot.plugin_manager.commands.values()), key=attrgetter("name")
        ):
            # use set to remove duplicate commands (from multiple aliases),
            # and sorted to sort by name

            if plugin.permissions:
                # check permissions
                allowed = False
                for perm in plugin.permissions:
                    if event.has_permission(perm, notice=False):
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
                event.notice(line)
            else:
                # This is an user in this case.
                event.message(line)

        event.notice(DETAIL_HELP_MSG.format(triggered_prefix))


@hook.command
def cmdinfo(text, bot, notice):
    """<command> - Gets various information about a command"""
    name = text.split()[0]
    cmds = list(get_potential_commands(bot, name))
    if not cmds:
        notice("Unknown command: '{}'".format(name))
        return

    if len(cmds) > 1:
        commands = sorted([command for command, _ in cmds])
        notice(
            "Possible matches: {}".format(formatting.get_text_list(commands))
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


def encode_doc(doc: str) -> str:
    return (
        doc.replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("[", "&lt;")
        .replace("]", "&gt;")
    )


@hook.command(permissions=["botcontrol"], autohelp=False)
def generatehelp(conn, bot):
    """
    - Dumps a list of commands with their help text to the docs directory
    formatted using markdown.
    """
    message = "{} Command list\n".format(conn.nick)
    message += "------\n"
    no_doc = "**{}**: Command has no documentation.\n\n"

    # use set to remove duplicate commands (from multiple aliases),
    # and sorted to sort by name
    command_hooks = bot.plugin_manager.commands.values()
    commands = sorted(set(command_hooks), key=attrgetter("name"))
    for plugin in commands:
        command = plugin.name
        doc = plugin.doc
        permission = ", ".join(plugin.permissions)
        alias_lst = [alias for alias in plugin.aliases if alias != command]

        aliases = ", ".join(alias_lst)
        if doc:
            doc = encode_doc(doc)
            if aliases:
                message += "**{} ({}):** {}\n\n".format(command, aliases, doc)
            else:
                # No aliases so just print the commands
                message += "**{}**: {}\n\n".format(command, doc)
        else:
            message += no_doc.format(command)

        if permission:
            message = message[:-2]
            message += " ( *Permission required:* {})\n\n".format(permission)

    # toss the markdown text into a paste
    return web.paste(message)
