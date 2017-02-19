from cloudbot import hook


@hook.command
def conncheck(nick, bot, notice): 
    """This command is an effort to make the bot reconnect to a network if it has been disconnected."""
    # For each irc network return a notice on the connection state and send a message from
    # each connection to the nick that used the command.
    for conn in bot.connections:
        # I am not sure if the connected property is ever changed.
        notice("{}, {}".format(conn, bot.connections[conn].connected))
        # if the value is in fact false try to connect
        if not bot.connections[conn].connected:
            bot.connections[conn].connect()
        # Send a message from each irc network connection to the nick that issued the command
        bot.connections[conn].message(nick, "just letting you know I am here. {}".format(conn))
