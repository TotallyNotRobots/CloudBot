# Author: Matheus Fillipe
# Date: 05/11/2022
# Description: Farting in Python
# Inspired by: https://github.com/RohanGautam/fart


import random
from tempfile import NamedTemporaryFile

import requests
from pydub import AudioSegment

from cloudbot import hook


def get_latest_line(conn, chan, nick):
    for name, _, msg in reversed(conn.history.get(chan.casefold(), [])):
        if nick.casefold() == name.casefold():
            # Ignore commands
            if msg.startswith(conn.config["command_prefix"]):
                continue
            return msg


def count_syllables(word: str) -> int:
    """Counts the number of syllables in a word."""
    count = 0
    vowels = "aeiouy"
    word = word.lower().strip(".:;?!")
    if word[0] in vowels:
        count += 1
    for index in range(1, len(word)):
        if word[index] in vowels and word[index - 1] not in vowels:
            count += 1
    if word.endswith("e"):
        count -= 1
    if word.endswith("le"):
        count += 1
    if count == 0:
        count += 1
    return count


def randomize_audio(audio: AudioSegment) -> AudioSegment:
    """Slightly changes the pitch and speed of the audio."""
    frame_rate: int = audio.frame_rate  # type: ignore
    delta = 20000
    changed = audio._spawn(
        audio.raw_data,
        overrides={
            "frame_rate": random.randint(frame_rate - delta, frame_rate + delta)
        },
    )
    return changed


def fart_sentence(audio: str, sentence: str) -> AudioSegment:
    """
    Farts out a sentence. For example 'hello world' becomes 'toot-toot toot'.

    :param audio bytes: The path for the base fart audio.
    :param sentence str: The sentence to fart out.
    :rtype bytes: wav audio
    """

    fart = AudioSegment.empty()
    audio = AudioSegment.from_wav(audio)
    words = sentence.strip().casefold().split()
    syllables_counts = [count_syllables(word) for word in words]
    syllable_audio = audio[:-500]
    end_audio = audio[:-100]
    print(syllables_counts)
    for fart_n in syllables_counts:
        for _ in range(fart_n - 1):
            fart += randomize_audio(syllable_audio)
        fart += randomize_audio(end_audio)

    return fart


def upload_file(file):
    url = "https://ttm.sh"
    payload = {"file": file}
    response = requests.request("POST", url, files=payload)
    return response.text.strip()


def fart_text(text: str) -> str:
    with NamedTemporaryFile(suffix=".wav") as temp:
        fart_sentence("data/fart.wav", text).export(temp.name, format="wav")
        return upload_file(temp)


@hook.command("fart", autohelp=False)
def fart(text: str, conn, chan, nick, reply):
    """<sentence> - Farts out a sentence or someone."""
    if not text.strip():
        with NamedTemporaryFile(suffix=".wav") as temp:
            fart = randomize_audio(AudioSegment.from_wav("data/fart.wav"))
            fart.export(temp.name, format="wav")
            return upload_file(temp)

    nick = text.strip().split()[0]
    if text.strip() == nick:
        line = get_latest_line(conn, chan, nick)
        if line is not None:
            text = line
            if line.startswith("\x01ACTION"):
                text = line[8:].strip(" \x01")
    return fart_text(text)
