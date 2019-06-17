import random
import re
import urllib.parse
from json import JSONDecodeError

import requests

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util import colors, web

API_URL = 'http://api.wordnik.com/v4/'
WEB_URL = 'https://www.wordnik.com/words/{}'

ATTRIB_NAMES = {
    'ahd-legacy': 'AHD/Wordnik',
    'ahd': 'AHD/Wordnik',
    'ahd-5': 'AHD/Wordnik',
    'century': 'Century/Wordnik',
    'wiktionary': 'Wiktionary/Wordnik',
    'gcide': 'GCIDE/Wordnik',
    'wordnet': 'Wordnet/Wordnik',
}

# Strings
# TODO move all strings here
no_api = "This command requires an API key from wordnik.com."


class WordnikAPIError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def user_msg(self):
        return "There was a problem contacting the Wordnik API ({})".format(
            self.message
        )


class NoAPIKey(WordnikAPIError):
    def __init__(self):
        super().__init__(no_api)


class WordNotFound(WordnikAPIError):
    def __init__(self):
        super().__init__("Word not found")


ERROR_MAP = {
    'Not Found': WordNotFound,
}


def raise_error(data):
    try:
        error = data['error']
    except KeyError:
        raise WordnikAPIError("Unknown error, unable to retrieve error data")

    try:
        err = ERROR_MAP[error]()
    except KeyError:
        err = WordnikAPIError("Unknown error {!r}".format(error))

    raise err


def api_request(endpoint, params=(), **kwargs):
    kwargs.update(params)

    api_key = bot.config.get_api_key('wordnik')
    if not api_key:
        raise NoAPIKey()

    url = API_URL + endpoint

    kwargs['api_key'] = api_key
    with requests.get(url, params=kwargs) as response:
        try:
            data = response.json()
        except JSONDecodeError:
            # Raise any request errors we have
            response.raise_for_status()
            # If there weren't any, just fall back to raising the current error
            raise

        # Raise an exception if there's an error in the response
        if not response.ok:
            raise_error(data)

    return data


def sanitize(text):
    return urllib.parse.quote(text.translate({ord('\\'): None, ord('/'): None}))


def word_lookup(word, operation, params=(), **kwargs):
    kwargs.update(params)
    return api_request(
        "word.json/" + sanitize(word) + "/" + operation,
        kwargs,
    )


def format_attrib(attr_id):
    try:
        return ATTRIB_NAMES[attr_id]
    except KeyError:
        return attr_id.title() + '/Wordnik'


@hook.command("define", "dictionary")
def define(text, event):
    """<word> - Returns a dictionary definition from Wordnik for <word>."""
    try:
        json = word_lookup(text, "definitions", limit=1)
    except WordNotFound:
        return colors.parse(
            "I could not find a definition for $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    data = json[0]
    data['word'] = data['word']
    data['url'] = web.try_shorten(WEB_URL.format(data['word']))
    data['attrib'] = format_attrib(data['sourceDictionary'])
    return colors.parse(
        "$(b){word}$(b): {text} - {url} ({attrib})"
    ).format_map(data)


@hook.command("wordusage", "wordexample", "usage")
def word_usage(text, event):
    """<word> - Returns an example sentence showing the usage of <word>."""
    try:
        json = word_lookup(text, "examples", limit=10)
    except WordNotFound:
        return colors.parse(
            "I could not find any usage examples for $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    out = colors.parse("$(b){}$(b): ").format(text)
    example = random.choice(json['examples'])
    out += "{} ".format(example['text'])
    return out


@hook.command("pronounce", "sounditout")
def pronounce(text, event):
    """<word> - Returns instructions on how to pronounce <word> with an audio
    example."""
    try:
        json = word_lookup(text, "pronunciations", limit=5)
    except WordNotFound:
        return colors.parse(
            "Sorry, I don't know how to pronounce $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    out = colors.parse("$(b){}$(b): ").format(text)
    out += " • ".join([i['raw'] for i in json])

    try:
        json = word_lookup(text, "audio", limit=1)
    except WordNotFound:
        json = None
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    if json:
        url = web.try_shorten(json[0]['fileUrl'])
        out += " - {}".format(url)

    return out


@hook.command()
def synonym(text, event):
    """<word> - Returns a list of synonyms for <word>."""
    try:
        json = word_lookup(text, "relatedWords", {
            'relationshipTypes': 'synonym',
            'limitPerRelationshipType': 5
        })
    except WordNotFound:
        return colors.parse(
            "Sorry, I couldn't find any synonyms for $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    out = colors.parse("$(b){}$(b): ").format(text)
    out += " • ".join(json[0]['words'])

    return out


@hook.command()
def antonym(text, event):
    """<word> - Returns a list of antonyms for <word>."""
    try:
        json = word_lookup(text, "relatedWords", {
            'relationshipTypes': 'antonym',
            'limitPerRelationshipType': 5,
            'useCanonical': 'false'
        })
    except WordNotFound:
        return colors.parse(
            "Sorry, I couldn't find any antonyms for $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    out = colors.parse("$(b){}$(b): ").format(text)
    out += " • ".join(json[0]['words'])

    return out


# word of the day
@hook.command("word", "wordoftheday", autohelp=False)
def wordoftheday(text, event):
    """[date] - returns the word of the day. To see past word of the day
    enter use the format yyyy-MM-dd. The specified date must be after
    2009-08-10."""
    match = re.search(r'(\d\d\d\d-\d\d-\d\d)', text)
    date = ""
    if match:
        date = match.group(1)

    if date:
        params = {
            'date': date
        }
        day = date
    else:
        params = {}
        day = "today"

    try:
        json = api_request("words.json/wordOfTheDay", params)
    except WordNotFound:
        return "Sorry I couldn't find the word of the day"
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    word = json['word']
    note = json['note']
    pos = json['definitions'][0]['partOfSpeech']
    definition = json['definitions'][0]['text']
    out = "The word for $(bold){day}$(bold) is $(bold){word}$(bold): " \
          "$(dred)({pos})$(dred) $(cyan){note}$(cyan) " \
          "$(b)Definition:$(b) $(dgreen){definition}$(dgreen)"

    return colors.parse(out).format(
        day=day,
        word=word,
        pos=pos,
        note=note,
        definition=definition,
    )


# random word
@hook.command("wordrandom", "randomword", autohelp=False)
def random_word(event):
    """- Grabs a random word from wordnik.com"""
    try:
        json = api_request("words.json/randomWord", {
            'hasDictionarydef': 'true',
            'vulgar': 'true'
        })
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    word = json['word']
    return colors.parse("Your random word is $(b){}$(b).").format(word)
