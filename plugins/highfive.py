from cloudbot import hook
from random import choice


@hook.command("high5", "hi5", "highfive")
def highfive(nick, text):
    """Highfives the requested user"""
    highfives = [
        "tries to give {nick} a five up high but misses."
        "that was awkward",
        "gives {nick} a killer high-five",
        "gives {nick} an elbow-shattering high-five",
        "smashes {nick} up high",
        "slaps skin with {nick}",
        "{nick} winds up for a killer five but misses and falls flat on his face",
        "halfheartedly high-fives {nick}",
        "gives {nick} a smooth five down low",
        "gives {nick} a friendly high five",
        "starts to give {nick} a high five, but leaves them hanging",
        "performs an incomprehensible handshake with {nick} that identifies "
        "them as the very best of friends",
        "makes as if to high five {nick} but pulls his hand away at the last "
        "second",
        "leaves {nick} hanging",
        "offers a fist and {nick} pounds it"

    ]
    return nick + " " + choice(highfives).format(nick=text)
