import re

from chartlyrics import ChartLyricsClient
from chartlyrics.lyrics import Strophe

from cloudbot import hook
from cloudbot.util.queue import Queue

results_queue = Queue()
poped3 = Queue()


def pop3(results, reply, chan, nick):
    global poped3
    songs = []
    for i in range(3):
        try:
            song = results.pop()
            if isinstance(song, Strophe):
                reply(str(song).replace("\n", " - "))
                return

            songs.append(song)
            reply(f"{i+1}) {song.artist} - {song.song} - {song.songUrl}")
        except IndexError:
            reply("No [more] results found.")
            break
    poped3[chan][nick] = songs


@hook.command("lyricsn", "lyn", autohelp=False)
def lyricsn(text, bot, chan, nick, reply):
    """<nick> - Returns next search result for pkg command for nick or yours by default. Use lyricsn to paginate"""
    global results_queue
    results = results_queue[chan][nick]
    user = text.strip().split()[0] if text.strip() else ""
    if user:
        if user in results_queue[chan]:
            results = results_queue[chan][user]
        else:
            return f"Nick '{user}' has no queue."

    if len(results) == 0:
        return "No [more] results found."

    return pop3(results, reply, chan, nick)


def parse_args(text: str):
    args = re.match(r'\s*"(.+)"\s+"(.+)"\s*', text)
    if args:
        return args.groups()
    args = re.match(r'\s*(.+)\s+"(.+)"\s*', text)
    if args:
        return args.groups()
    args = re.match(r'\s*"(.+)"\s+(.+)\s*', text)
    if args:
        return args.groups()


@hook.command("lyrics", autohost=False)
def lyricsnmusic(text, chan, nick, reply):
    """<artist> <song> - will fetch the first 150 characters of a song and a link to the full lyrics. Enclose with quotes to deliminate arguments. Use lyricsn to paginate"""
    global results_queue
    args = text.split()
    if len(args) > 2 and '"' in text:
        args = parse_args(text)
    if args is None or len(args) != 2:
        return "Usage: .lyrics <artist> <song>"
    client = ChartLyricsClient()
    results_queue[chan][nick] = list(
        client.search_artist_and_song(args[0], args[1])
    )
    return pop3(results_queue[chan][nick], reply, chan, nick)


@hook.command("lysearch", autohelp=False)
def lysearch(text, chan, nick, reply):
    """<search_queue> - Searches for a song from its lyrics. Use lyricsn to paginate"""
    global results_queue
    if len(text.strip()) == 0:
        return "Usage: .lysearch <search_queue>"
    client = ChartLyricsClient()
    results_queue[chan][nick] = list(client.search_text(text))
    return pop3(results_queue[chan][nick], reply, chan, nick)


@hook.command("getlyrics", autohelp=False)
def getlyrics(text, chan, nick, reply):
    """<num> - will fetch the first verse of a song where 'num' is the number on the last list. Use 'lyricsn' to paginate."""
    global poped3, results_queue
    if len(text.strip()) == 0:
        return "Usage: .getlyrics <num>"
    if not text.strip().isdigit():
        return "Invalid number"
    num = int(text.strip())
    if num < 0:
        return "Number is too small"
    if num > len(poped3[chan][nick]):
        return "Number too big"
    i = 1
    song = poped3[chan][nick].pop()
    while i < num:
        song = poped3[chan][nick].pop()
        i += 1

    results_queue[chan][nick] = list(song.lyrics_object)  # list of strophes
    return pop3(results_queue[chan][nick], reply, chan, nick)
