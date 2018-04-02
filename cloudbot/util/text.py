"""
Basic text utilities
"""
import re

valid_command_re = re.compile(r'\w+')


def is_command(name):
    """
    Determine if a name is a valid command
    :param name: The name to validate
    :type name: str
    :return: True if the name is valid, False otherwise
    :rtype: bool
    """
    return bool(valid_command_re.fullmatch(name))
