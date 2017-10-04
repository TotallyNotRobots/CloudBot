"""
Core filters for IRC raw lines
"""

from cloudbot import hook
from cloudbot.hook import Priority

NEW_LINE_TRANS_TBL = str.maketrans({
    '\r': None,
    '\n': None,
    '\0': None,
})


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
    else:
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
