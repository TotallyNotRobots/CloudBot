def get_client():
    from cloudbot.clients.irc.client import IrcClient
    return IrcClient


def get_client_type():
    return "irc"
