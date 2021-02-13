"""
piglatin.py

Translates text into pig latin. Use the NLTK module to provide correct translation.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

Special Thanks:
    - Benjamin Hoffmeyer <https://github.com/TheDoctorsLife>
    - J.F. Sebastian <https://stackoverflow.com/users/4279/j-f-sebastian>

License:
    GPL v3
"""

import string
from typing import Dict, List

import nltk

from cloudbot import hook

pronunciations: Dict[str, List[List[str]]] = {}


# Translate functions by J.F. Sebastian
# <https://stackoverflow.com/questions/22773826/pig-latin-translator>


def translate(word: str):
    word = word.lower()  # NOTE: ignore Unicode casefold
    i = 0
    # find out whether the word start with a vowel sound using
    # the pronunciations dictionary
    for syllables in pronunciations.get(word, []):
        for i, syl in enumerate(syllables):
            is_vowel = syl[-1].isdigit()
            if is_vowel:
                break
        else:  # no vowels
            assert 0

        if i == 0:  # starts with a vowel
            return word + "way"

        if "y" in word:  # allow 'y' as a vowel for known words
            return translate_basic(word, vowels="aeiouy", start=i)

        break  # use only the first pronunciation

    return translate_basic(word, start=i)


def translate_basic(word, vowels="aeiou", start=0):
    word = word.lower()
    i = 0
    for i, c in enumerate(word[start:], start=start):
        if c in vowels:
            break
    else:  # no vowel in the word
        i += 1
    return word[i:] + word[:i] + "w" * (i == 0) + "ay" * word.isalnum()


@hook.on_start()
def load_nltk():
    nltk.download("cmudict")

    pronunciations.clear()
    pronunciations.update(nltk.corpus.cmudict.dict())


@hook.command("pig", "piglatin")
def piglatin(text):
    """<text> - Converts <text> to pig latin."""
    if not pronunciations:
        return "Please wait, getting NLTK ready!"

    words = []
    for word in text.split():
        if word[-1] in string.punctuation:
            end = word[-1]
            word = word[:-1]
        else:
            end = ""

        out_word = translate(word)

        if word.isupper() and not word == "I":
            out_word = out_word.upper()
        elif word[0].isupper():
            out_word = out_word.title()
        else:
            out_word = out_word.lower()

        words.append(out_word + end)

    if text.isupper():
        return " ".join(words).upper()

    return " ".join(words)
