Web interface:
    - Permission management
        - Adding users to groups
        - Checking permissions
        - Managing groups
    - Connection management
        - Adding new connections
        - Modifying connection settings
        - Reconnecting connections

New Plugins:
    hunt.py:
        - Generic version of duckhunt
        - All hunt configs defined in data/games
        - Variable targets, hunt names, action types, etc

    reddit_sub_track.py:
        - Monitor a subreddit for new posts

Client Changes:
    - Abstract `User` and `Channel` objects
        - Store user/channel names
        - Store member relationships for users and channels
    - Abstract message formatting system
        - Colors, bold, etc
    - Abstract `Message` objects
        - Hold the message context, sender, target, etc

Event Changes:
    - Remove client specific fields from the base `Event` class

Hook API Changes:
    - Move full `Hook` classes to `hook.py` and have each type return its "full" type (eg _CommandHook -> CommandHook)

Plugin API Changes:
    - Client specific hooks should all set the `clients=` keyword in their `@hook` call
    - Move sieves to standard hook launching system
    - Change logic for whether a hook is sieved to use a field on the hook object itself
