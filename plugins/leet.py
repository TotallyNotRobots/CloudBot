from cloudbot import hook
import unidecode

origspace = "abcdefghijklmnopqrstuvwxyz"
keyspace = "4bcd3fg81jk7mn0pqr57uvwxy2"

@hook.command("leet", "leetify", "l33t", "1337")
def leet(text, bot, nick):
    """<text> - Converts text to leet"""
    text = unidecode.unidecode(text)
    out = ""
    for origc in text:
        if origc in origspace:
            out += keyspace[origspace.index(origc)]
        else:
            out += origc
    return out
