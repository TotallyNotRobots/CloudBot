import logging
import random
import re
import urllib.parse
from json import JSONDecodeError
from typing import Any, Dict, Iterable, List, Optional, Tuple, cast

import requests

from cloudbot import hook
from cloudbot.bot import bot
from cloudbot.util import colors, web
from cloudbot.util.http import GetParams

logger = logging.getLogger("cloudbot")

API_URL = "https://api.wordnik.com/v4/"
WEB_URL = "https://www.wordnik.com/words/{}"

ATTRIB_NAMES = {
    "ahd-legacy": "AHD/Wordnik",
    "ahd": "AHD/Wordnik",
    "ahd-5": "AHD/Wordnik",
    "century": "Century/Wordnik",
    "wiktionary": "Wiktionary/Wordnik",
    "gcide": "GCIDE/Wordnik",
    "wordnet": "Wordnet/Wordnik",
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


class NoValidResults(WordnikAPIError):
    def __init__(self, term, results):
        super().__init__("No valid results found for {!r}".format(term))
        self.term = term
        self.results = results


ERROR_MAP = {"Not Found": WordNotFound}


def raise_error(data):
    try:
        error = data["error"]
    except KeyError as e:
        raise WordnikAPIError(
            "Unknown error, unable to retrieve error data"
        ) from e

    err: Exception
    try:
        err = ERROR_MAP[error]()
    except KeyError:
        err = WordnikAPIError("Unknown error {!r}".format(error))

    raise err


def api_request(endpoint: str, params=(), **kwargs) -> List[Dict[str, Any]]:
    kwargs.update(params)

    api_key = bot.config.get_api_key("wordnik")
    if not api_key:
        raise NoAPIKey()

    url = API_URL + endpoint

    kwargs["api_key"] = api_key
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


def api_request_single(endpoint: str, params=(), **kwargs) -> Dict[str, Any]:
    return cast(Dict[str, Any], api_request(endpoint, params, **kwargs))


class WordLookupRequest:
    def __init__(
        self,
        word: str,
        operation: str,
        *,
        required_fields: Tuple[str, ...] = (),
    ) -> None:
        self.word = word
        self.operation = operation
        self.required_fields = required_fields
        self.extra_params: GetParams = {}
        self.result_limit = 5
        self.max_tries = 3

    @staticmethod
    def sanitize(text: str) -> str:
        return urllib.parse.quote(
            text.translate({ord("\\"): None, ord("/"): None})
        )

    @property
    def endpoint(self) -> str:
        return "word.json/" + self.sanitize(self.word) + "/" + self.operation

    def get_params(self) -> GetParams:
        params = dict(self.extra_params)
        if self.result_limit:
            params["limit"] = self.result_limit

        return params

    def get_results(self) -> List[Dict[str, Any]]:
        data = api_request(self.endpoint, params=self.get_params())

        return data

    def is_result_valid(self, result: Dict[str, Any]) -> bool:
        for field in self.required_fields:
            if field not in result:
                return False

        return True

    def get_filtered_results(
        self, min_results: int = 1
    ) -> Iterable[Dict[str, Any]]:
        count = 0
        tries = 0
        results = []
        while tries < self.max_tries:
            tries += 1
            for result in self.get_results():
                results.append(result)
                if self.is_result_valid(result):
                    count += 1
                    yield result

            if count >= min_results:
                return

            self.result_limit *= 2

        if count:
            # We didn't hit the minimum but we got some at least
            logger.warning(
                "[wordnik] Got %d valid results, wanted at least %d. "
                "Continuing anyways",
                count,
                min_results,
            )
            return

        raise NoValidResults(self.word, results)

    def first(self) -> Optional[Dict[str, Any]]:
        for item in self.get_filtered_results():
            return item

        return None

    def random(self) -> Dict[str, Any]:
        return random.choice(list(self.get_filtered_results()))


class DefinitionsLookupRequest(WordLookupRequest):
    def __init__(self, word):
        super().__init__(word, "definitions", required_fields=("text",))


class ExamplesLookupRequest(WordLookupRequest):
    def __init__(self, word):
        super().__init__(word, "examples")
        self.result_limit = 10

    def get_results(self):
        return api_request_single(self.endpoint, params=self.get_params())[
            "examples"
        ]


class PronounciationLookupRequest(WordLookupRequest):
    def __init__(self, word):
        super().__init__(word, "pronunciations", required_fields=("raw",))


class AudioLookupRequest(WordLookupRequest):
    def __init__(self, word):
        super().__init__(word, "audio", required_fields=("fileUrl",))


class RelatedLookupRequest(WordLookupRequest):
    def __init__(self, word, rel_type):
        super().__init__(word, "relatedWords", required_fields=("words",))
        self.extra_params["relationshipTypes"] = rel_type

    def get_params(self):
        params = super().get_params()
        params.pop("limit", None)

        params["limitPerRelationshipType"] = self.result_limit

        return params


def format_attrib(attr_id):
    try:
        return ATTRIB_NAMES[attr_id]
    except KeyError:
        return attr_id.title() + "/Wordnik"


@hook.command("define", "dictionary")
def define(text, event):
    """<word> - Returns a dictionary definition from Wordnik for <word>."""
    lookup = DefinitionsLookupRequest(text)
    try:
        data = lookup.first()
    except WordNotFound:
        return colors.parse(
            "I could not find a definition for $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    data["url"] = web.try_shorten(WEB_URL.format(data["word"]))
    data["attrib"] = format_attrib(data["sourceDictionary"])

    return colors.parse("$(b){word}$(b): {text} - {url} ({attrib})").format_map(
        data
    )


@hook.command("wordusage", "wordexample", "usage")
def word_usage(text, event):
    """<word> - Returns an example sentence showing the usage of <word>."""
    lookup = ExamplesLookupRequest(text)
    try:
        example = lookup.random()
    except WordNotFound:
        return colors.parse(
            "I could not find any usage examples for $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    out = colors.parse("$(b){word}$(b): {text}").format(
        word=text, text=example["text"]
    )
    return out


@hook.command("pronounce", "sounditout")
def pronounce(text, event):
    """<word> - Returns instructions on how to pronounce <word> with an audio
    example."""
    lookup = PronounciationLookupRequest(text)
    try:
        pronounce_response = list(lookup.get_filtered_results())[:5]
    except WordNotFound:
        return colors.parse(
            "Sorry, I don't know how to pronounce $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    out = colors.parse("$(b){}$(b): ").format(text)
    out += " • ".join([i["raw"] for i in pronounce_response])

    audio_lookup = AudioLookupRequest(text)
    try:
        audio_response = audio_lookup.first()
    except WordNotFound:
        pass
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise
    else:
        url = web.try_shorten(audio_response["fileUrl"])
        out += " - {}".format(url)

    return out


@hook.command()
def synonym(text, event):
    """<word> - Returns a list of synonyms for <word>."""
    lookup = RelatedLookupRequest(text, "synonym")
    try:
        data = lookup.first()
    except WordNotFound:
        return colors.parse(
            "Sorry, I couldn't find any synonyms for $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    out = colors.parse("$(b){}$(b): ").format(text)
    out += " • ".join(data["words"])

    return out


@hook.command()
def antonym(text, event):
    """<word> - Returns a list of antonyms for <word>."""
    lookup = RelatedLookupRequest(text, "antonym")
    lookup.extra_params["useCanonical"] = "false"
    try:
        data = lookup.first()
    except WordNotFound:
        return colors.parse(
            "Sorry, I couldn't find any antonyms for $(b){}$(b)."
        ).format(text)
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    out = colors.parse("$(b){}$(b): ").format(text)
    out += " • ".join(data["words"])

    return out


# word of the day
@hook.command("word", "wordoftheday", autohelp=False)
def wordoftheday(text, event):
    """[date] - returns the word of the day. To see past word of the day
    enter use the format yyyy-MM-dd. The specified date must be after
    2009-08-10."""
    match = re.search(r"(\d\d\d\d-\d\d-\d\d)", text)
    date = ""
    if match:
        date = match.group(1)

    if date:
        params = {"date": date}
        day = date
    else:
        params = {}
        day = "today"

    try:
        json = api_request_single("words.json/wordOfTheDay", params)
    except WordNotFound:
        return "Sorry I couldn't find the word of the day"
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    word = json["word"]
    note = json["note"]
    pos = json["definitions"][0]["partOfSpeech"]
    definition = json["definitions"][0]["text"]
    out = (
        "The word for $(bold){day}$(bold) is $(bold){word}$(bold): "
        "$(dred)({pos})$(dred) $(cyan){note}$(cyan) "
        "$(b)Definition:$(b) $(dgreen){definition}$(dgreen)"
    )

    return colors.parse(out).format(
        day=day, word=word, pos=pos, note=note, definition=definition
    )


# random word
@hook.command("wordrandom", "randomword", autohelp=False)
def random_word(event):
    """- Grabs a random word from wordnik.com"""
    try:
        json = api_request_single(
            "words.json/randomWord",
            {"hasDictionarydef": "true", "vulgar": "true"},
        )
    except WordnikAPIError as e:
        event.reply(e.user_msg())
        raise

    word = json["word"]
    return colors.parse("Your random word is $(b){}$(b).").format(word)
