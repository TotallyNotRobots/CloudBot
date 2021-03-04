"""
Core filters for IRC raw lines
"""

from cloudbot import hook
from cloudbot.hook import Priority
from cloudbot.util import colors

NEW_LINE_TRANS_TBL = str.maketrans(
    {
        "\r": None,
        "\n": None,
        "\0": None,
    }
)


@hook.irc_out(priority=Priority.HIGHEST)
def strip_newlines(line, conn):
    """
    Removes newline characters from a message
    :param line: str
    :param conn: cloudbot.clients.irc.IrcClient
    :return: str
    """
    do_strip = conn.config.get("strip_newlines", True)
    if do_strip:
        return line.translate(NEW_LINE_TRANS_TBL)

    return line


@hook.irc_out(priority=Priority.HIGH)
def truncate_line(line, conn):
    line_len = conn.config.get("max_line_length", 510)
    return line[:line_len] + "\r\n"


@hook.irc_out(priority=Priority.LOWEST)
def encode_line(line, conn):
    if not isinstance(line, str):
        return line

    encoding = conn.config.get("encoding", "utf-8")
    errors = conn.config.get("encoding_errors", "replace")
    return line.encode(encoding, errors)


@hook.irc_out(priority=Priority.HIGH)
def strip_command_chars(parsed_line, conn, line):
    chars = conn.config.get("strip_cmd_chars", "!.@;$")
    if (
        chars
        and parsed_line
        and parsed_line.command == "PRIVMSG"
        and parsed_line.parameters[-1][0] in chars
    ):
        new_msg = (
            colors.parse("$(red)[!!]$(clear) ") + parsed_line.parameters[-1]
        )
        parsed_line.parameters[-1] = new_msg
        parsed_line.has_trail = True
        return parsed_line

    return line
