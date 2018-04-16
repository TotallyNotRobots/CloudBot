def get_client():
    from .client import IrcClient
    return IrcClient


def get_client_type():
    return "irc"
