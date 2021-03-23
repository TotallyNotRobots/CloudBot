import json
from unittest.mock import MagicMock

import pytest
import requests

from plugins import wordnik


@pytest.mark.parametrize(
    "source,name",
    [
        ("ahd", "AHD/Wordnik"),
        ("ahd-5", "AHD/Wordnik"),
        ("ahd-6", "Ahd-6/Wordnik"),
        ("foobar", "Foobar/Wordnik"),
    ],
)
def test_attr_name(source, name):
    assert wordnik.format_attrib(source) == name


class WordTestBase:
    @classmethod
    def get_op(cls):
        raise NotImplementedError

    @classmethod
    def get_paramstring(cls):
        return None

    @classmethod
    def get_result_limit(cls):
        return 5

    @classmethod
    def build_url(cls, word, op=None, paramstring=None):
        base = "http://api.wordnik.com/v4/word.json"
        url = base + "/" + word + "/" + (op or cls.get_op())
        if cls.get_result_limit():
            param_trail = "limit={}&api_key=APIKEY".format(
                cls.get_result_limit()
            )
        else:
            param_trail = "api_key=APIKEY"

        params = paramstring or cls.get_paramstring()
        if params:
            params += "&" + param_trail
        else:
            params = param_trail

        return url + "?" + params

    @classmethod
    def get_func(cls):
        raise NotImplementedError

    @classmethod
    def call(cls, text, event=None):
        if event is None:
            event = MagicMock()

        return cls.get_func()(text, event), event

    @classmethod
    def get_not_found_msg(cls, word):
        raise NotImplementedError

    def test_not_found(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("word"),
            match_querystring=True,
            status=404,
            json={"error": "Not Found"},
        )

        out, _ = self.call("word")
        assert out == self.get_not_found_msg("word")

    def test_unknown(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("word"),
            match_querystring=True,
            status=512,
            json={"error": "FooBar"},
        )

        event = MagicMock()
        with pytest.raises(wordnik.WordnikAPIError):
            self.call("word", event)

        event.reply.assert_called_with(
            "There was a problem contacting the Wordnik API (Unknown error 'FooBar')"
        )

    def test_invalid_error(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("word"),
            match_querystring=True,
            status=512,
            json={},
        )

        event = MagicMock()
        with pytest.raises(wordnik.WordnikAPIError):
            self.call("word", event)

        event.reply.assert_called_with(
            "There was a problem contacting the Wordnik API "
            "(Unknown error, unable to retrieve error data)"
        )

    def test_json_http_error(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("word"),
            match_querystring=True,
            status=512,
            body="Some data",
        )

        event = MagicMock()
        with pytest.raises(requests.HTTPError):
            self.call("word", event)

    def test_json_no_http_error(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("word"),
            match_querystring=True,
            body="Some data",
        )

        event = MagicMock()
        with pytest.raises(json.JSONDecodeError):
            self.call("word", event)

    def test_no_key(self, mock_requests, mock_api_keys):
        mock_api_keys.config.get_api_key.return_value = None

        mock_event = MagicMock()

        with pytest.raises(wordnik.NoAPIKey):
            self.call("word", mock_event)

        mock_event.reply.assert_called_with(
            "There was a problem contacting the Wordnik API "
            "(This command requires an API key from wordnik.com.)"
        )


class TestDefine(WordTestBase):
    @classmethod
    def get_func(cls):
        return wordnik.define

    @classmethod
    def get_op(cls):
        return "definitions"

    @classmethod
    def get_not_found_msg(cls, word):
        return "I could not find a definition for \x02{}\x02.".format(word)

    def test_search(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("word"),
            match_querystring=True,
            json=[
                {
                    "id": "W5229000-1",
                    "partOfSpeech": "noun",
                    "attributionText": (
                        "from The American Heritage® Dictionary of the "
                        "English Language, 5th Edition."
                    ),
                    "sourceDictionary": "ahd-5",
                    "text": (
                        "A sound or a combination of sounds, or its "
                        "representation in writing or printing, that symbolizes "
                        "and communicates a meaning and may consist of a single "
                        "morpheme or of a combination of morphemes."
                    ),
                    "sequence": "1",
                    "score": 0,
                    "labels": [],
                    "citations": [],
                    "word": "word",
                    "relatedWords": [],
                    "exampleUses": [],
                    "textProns": [],
                    "notes": [],
                    "attributionUrl": "https://ahdictionary.com/",
                    "wordnikUrl": "https://www.wordnik.com/words/word",
                }
            ],
        )

        expected = (
            "\x02word\x02: A sound or a combination of sounds, or its "
            "representation in writing or printing, that symbolizes and "
            "communicates a meaning and may consist of a single morpheme "
            "or of a combination of morphemes. "
            "- https://www.wordnik.com/words/word (AHD/Wordnik)"
        )

        out, _ = self.call("word")
        assert out == expected


class TestUsage(WordTestBase):
    @classmethod
    def get_func(cls):
        return wordnik.word_usage

    @classmethod
    def get_op(cls):
        return "examples"

    @classmethod
    def get_result_limit(cls):
        return 10

    @classmethod
    def get_not_found_msg(cls, word):
        return "I could not find any usage examples for \x02{}\x02.".format(
            word
        )

    def test_search(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("word"),
            match_querystring=True,
            json={
                "examples": [
                    {
                        "provider": {"id": 711},
                        "year": 2006,
                        "rating": 9625.236,
                        "url": (
                            "http://plato.stanford.edu/archives/fall2009/"
                            "entries/types-tokens/"
                        ),
                        "word": "word",
                        "text": (
                            "There is an important and very common use of "
                            "the word ˜word™ that lexicographers and the "
                            "rest of us use frequently."
                        ),
                        "documentId": 22333003,
                        "exampleId": 563509621,
                        "title": "Types and Tokens",
                        "author": "Wetzel, Linda",
                    }
                ]
            },
        )

        expected = (
            "\x02word\x02: There is an important and very common "
            "use of the word ˜word™ that lexicographers and the rest "
            "of us use frequently."
        )

        out, _ = self.call("word")
        assert out == expected


class TestPronounce(WordTestBase):
    @classmethod
    def get_func(cls):
        return wordnik.pronounce

    @classmethod
    def get_op(cls):
        return "pronunciations"

    @classmethod
    def get_not_found_msg(cls, word):
        return "Sorry, I don't know how to pronounce \x02word\x02."

    def _init_search(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("word"),
            match_querystring=True,
            json=[
                {
                    "seq": 0,
                    "raw": "wûrd",
                    "rawType": "ahd-5",
                    "id": "W5229000",
                    "attributionText": (
                        "from The American Heritage® Dictionary of the English "
                        "Language, 5th Edition."
                    ),
                    "attributionUrl": "https://ahdictionary.com/",
                },
                {
                    "seq": 0,
                    "raw": "W ER1 D",
                    "rawType": "arpabet",
                    "attributionText": "from The CMU Pronouncing Dictionary.",
                    "attributionUrl": (
                        "http://www.speech.cs.cmu.edu/cgi-bin/cmudict"
                    ),
                },
                {
                    "seq": 0,
                    "raw": "/wɜː(ɹ)d/",
                    "rawType": "IPA",
                    "attributionText": (
                        "from Wiktionary, Creative Commons "
                        "Attribution/Share-Alike License."
                    ),
                    "attributionUrl": (
                        "http://creativecommons.org/licenses/by-sa/3.0/"
                    ),
                },
                {
                    "seq": 0,
                    "raw": "/wɝd/",
                    "rawType": "IPA",
                    "attributionText": "from Wiktionary, Creative Commons "
                    "Attribution/Share-Alike License.",
                    "attributionUrl": "http://creativecommons.org/licenses"
                    "/by-sa/3.0/",
                },
            ],
        )

    def test_search(self, mock_requests, mock_api_keys):
        self._init_search(mock_requests, mock_api_keys)

        mock_requests.add(
            "GET",
            self.build_url("word", "audio"),
            match_querystring=True,
            json=[{"fileUrl": "https://example.com/word.ogg"}],
        )

        expected = (
            "\x02word\x02: wûrd • W ER1 D • /wɜː(ɹ)d/ • /wɝd/ - "
            "https://example.com/word.ogg"
        )

        out, _ = self.call("word")
        assert out == expected

    def test_search_no_audio(self, mock_requests, mock_api_keys):
        self._init_search(mock_requests, mock_api_keys)

        mock_requests.add(
            "GET",
            self.build_url("word", "audio"),
            match_querystring=True,
            status=404,
            json={"error": "Not Found"},
        )

        expected = "\x02word\x02: wûrd • W ER1 D • /wɜː(ɹ)d/ • /wɝd/"

        out, _ = self.call("word")
        assert out == expected

    def test_search_audio_error(self, mock_requests, mock_api_keys):
        self._init_search(mock_requests, mock_api_keys)

        mock_requests.add(
            "GET",
            self.build_url("word", "audio"),
            match_querystring=True,
            status=500,
            json={"error": "FooBar"},
        )

        event = MagicMock()
        with pytest.raises(wordnik.WordnikAPIError):
            self.call("word", event)

        event.reply.assert_called_with(
            "There was a problem contacting the Wordnik API (Unknown error 'FooBar')"
        )


class TestSynonym(WordTestBase):
    @classmethod
    def get_func(cls):
        return wordnik.synonym

    @classmethod
    def get_op(cls):
        return "relatedWords"

    @classmethod
    def get_result_limit(cls):
        return None

    @classmethod
    def get_paramstring(cls):
        return "relationshipTypes=synonym&limitPerRelationshipType=5"

    @classmethod
    def get_not_found_msg(cls, word):
        return "Sorry, I couldn't find any synonyms for \x02{}\x02.".format(
            word
        )

    def test_search(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("word"),
            match_querystring=True,
            json=[
                {
                    "relationshipType": "synonym",
                    "words": [
                        "Bible",
                        "Bible oath",
                        "God",
                        "Logos",
                        "Parthian shot",
                    ],
                }
            ],
        )

        expected = (
            "\x02word\x02: Bible • Bible oath • God • Logos • Parthian shot"
        )

        out, _ = self.call("word")
        assert out == expected


class TestAntonym(WordTestBase):
    @classmethod
    def get_func(cls):
        return wordnik.antonym

    @classmethod
    def get_op(cls):
        return "relatedWords"

    @classmethod
    def get_result_limit(cls):
        return None

    @classmethod
    def get_paramstring(cls):
        return "relationshipTypes=antonym&limitPerRelationshipType=5&useCanonical=false"

    @classmethod
    def get_not_found_msg(cls, word):
        return "Sorry, I couldn't find any antonyms for \x02{}\x02.".format(
            word
        )

    def test_search(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url("clear"),
            match_querystring=True,
            json=[
                {
                    "relationshipType": "antonym",
                    "words": ["cloudy", "obscure", "thick"],
                }
            ],
        )

        expected = "\x02clear\x02: cloudy • obscure • thick"

        out, _ = self.call("clear")
        assert out == expected


class WordsTestBase(WordTestBase):
    @classmethod
    def get_func(cls):
        raise NotImplementedError

    @classmethod
    def get_op(cls):
        raise NotImplementedError

    @classmethod
    def get_not_found_msg(cls, word):
        raise NotImplementedError

    @classmethod
    def build_url(cls, word=None, op=None, paramstring=None):
        base = "http://api.wordnik.com/v4/words.json"
        url = base + "/" + (op or cls.get_op())
        return (
            url
            + "?"
            + "&".join(
                filter(
                    None,
                    ((paramstring or cls.get_paramstring()), "api_key=APIKEY"),
                )
            )
        )


class TestWOTD(WordsTestBase):
    @classmethod
    def get_not_found_msg(cls, word):
        return "Sorry I couldn't find the word of the day"

    @classmethod
    def get_op(cls):
        return "wordOfTheDay"

    @classmethod
    def get_func(cls):
        return wordnik.wordoftheday

    def test_today(self, mock_requests, mock_api_keys):
        definitions = [
            {
                "source": "wiktionary",
                "text": (
                    "(in science fiction) a psychic ability to control electronic "
                    "machinery and/or read electronic signals, especially hardware."
                ),
                "note": None,
                "partOfSpeech": "noun",
            }
        ]
        examples = [
            {
                "url": "http://www.superheronation.com/2009/08/25/foxs-review-forum/",
                "title": (
                    "Superhero Nation: how to write superhero novels and comic "
                    "books &raquo; Fox’s Review Forum"
                ),
                "text": (
                    "Powers I have in mind for other main characters are "
                    "probability manipulation, super intelligence, and technopathy."
                ),
                "id": 1101722947,
            }
        ]
        note = (
            "The word 'technopathy' comes from Greek roots meaning 'skill' and "
            "'suffering'."
        )
        mock_requests.add(
            "GET",
            self.build_url(),
            match_querystring=True,
            json={
                "_id": "5cfaf4960464123a364fd4fd",
                "word": "technopathy",
                "contentProvider": {"name": "wordnik", "id": 711},
                "definitions": definitions,
                "publishDate": "2019-06-17T03:00:00.000Z",
                "examples": examples,
                "pdd": "2019-06-17",
                "htmlExtra": None,
                "note": note,
            },
        )

        out, _ = self.call("")

        expected = (
            "The word for \x02today\x02 is \x02technopathy\x02: \x0305(noun)\x0305 "
            "\x0310The word 'technopathy' comes from Greek roots meaning 'skill' and "
            "'suffering'.\x0310 \x02Definition:\x02 \x0303(in science fiction) a "
            "psychic ability to control electronic machinery and/or read electronic "
            "signals, especially hardware.\x0303"
        )

        assert out == expected

    def test_date(self, mock_requests, mock_api_keys):
        definitions = [
            {
                "text": (
                    "To mix with water and sweeten; make sangaree of: "
                    "as, to sangaree port-wine."
                ),
                "partOfSpeech": "verb",
                "source": "century",
                "note": None,
            },
            {
                "text": (
                    "Wine, more especially red wine diluted with water, sweetened, "
                    "and flavored with nutmeg, used as a cold drink. Varieties of "
                    "it are named from the wine employed: as, port-wine sangaree."
                ),
                "partOfSpeech": "noun",
                "source": "century",
                "note": None,
            },
        ]

        examples = [
            {
                "url": (
                    "http://api.wordnik.com/v4/mid/"
                    "7767857a6a9b9e4f378ab2fdf73d93ca6fffc02a3e50cd92be465d0e2276df30"
                ),
                "text": (
                    "But, when we became better acquainted — which was while "
                    "Charker and I were drinking sugar-cane sangaree, which "
                    "she made in a most excellent manner — I found that her "
                    "Christian name was Isabella, which they shortened into "
                    "Bell, and that the name of the deceased non-commissioned "
                    "officer was Tott."
                ),
                "title": "The Perils of Certain English Prisoners",
                "id": 1094134527,
            },
            {
                "url": (
                    "http://api.wordnik.com/v4/mid/"
                    "7e003ed62c2faddb52212251bd929b1d67b24a69fda3a0c2b2efece1b6008e90"
                ),
                "text": (
                    "Administrador woke us all up, and gleefully presented us "
                    "with an enormous bowl of sangaree, made of the remains of "
                    "the Bordeaux and the brandy and the pisco, and plenty of "
                    "ice, -- ice this time, -- and sugar, and limes, and slices "
                    "of pineapple, Madam, -- the which he had concocted during "
                    "our slumber."
                ),
                "title": "The Atlantic Monthly, Volume 15, "
                "No. 87, January, 1865",
                "id": 1087980293,
            },
            {
                "url": (
                    "http://api.wordnik.com/v4/mid/"
                    "b051be319d7935b65edb84e6b1fa74dc1a978ed6787e82d19b7dfca343c8c6dc"
                ),
                "text": (
                    "In anticipation of the hot weather, I had laid in a large "
                    "stock of raspberry vinegar, which, properly managed, helps "
                    "to make a pleasant drink; and there was a great demand for "
                    "sangaree, claret, and cider cups, the cups being battered "
                    "pewter pots."
                ),
                "title": "Wonderful Adventures of Mrs. Seacole in Many Lands",
                "id": 1095843424,
            },
            {
                "url": (
                    "http://api.wordnik.com/v4/mid/"
                    "baf84d8de4707ffdfdbc58cc8deb717fe110573f734f4ebdb5a3b2e2bccb6777"
                ),
                "text": (
                    "A sangaree or any other delicacy, taken while resting after "
                    "a walk which taxed the weakened energies to the utmost, or a "
                    "meal served outside the fevered air of the wards, did more to "
                    "build up the strength than any amount of medicine could have done."
                ),
                "title": (
                    "Memories A Record of Personal Experience and Adventure During "
                    "Four Years of War"
                ),
                "id": 1175960432,
            },
        ]

        mock_requests.add(
            "GET",
            self.build_url(paramstring="date=2018-11-21"),
            match_querystring=True,
            json={
                "_id": "5c60c1a77c27cbdb29216227",
                "word": "sangaree",
                "publishDate": "2018-11-21T03:00:00.000Z",
                "contentProvider": {"name": "wordnik", "id": 711},
                "note": "The word 'sangaree' is related to the Spanish word 'sangria'.",
                "htmlExtra": None,
                "pdd": "2018-11-21",
                "definitions": definitions,
                "examples": examples,
            },
        )

        out, _ = self.call("2018-11-21")

        expected = (
            "The word for \x022018-11-21\x02 is \x02sangaree\x02: \x0305(verb)\x0305 "
            "\x0310The word 'sangaree' is related to the Spanish word 'sangria'.\x0310 "
            "\x02Definition:\x02 \x0303To mix with water and sweeten; make sangaree "
            "of: as, to sangaree port-wine.\x0303"
        )

        assert out == expected


class TestRandomWord(WordsTestBase):
    @classmethod
    def get_op(cls):
        return "randomWord"

    @classmethod
    def get_paramstring(cls):
        return "hasDictionarydef=true&vulgar=true"

    @classmethod
    def get_not_found_msg(cls, word):
        return "There was a problem contacting the Wordnik API (Word not found)"

    @classmethod
    def get_func(cls):
        return wordnik.random_word

    @classmethod
    def call(cls, text=None, event=None):
        if event is None:
            event = MagicMock()

        return cls.get_func()(event), event

    def test_not_found(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url(),
            match_querystring=True,
            status=404,
            json={"error": "Not Found"},
        )

        event = MagicMock()
        with pytest.raises(wordnik.WordNotFound):
            self.call("word", event)

        event.reply.assert_called_with(self.get_not_found_msg("word"))

    def test_random(self, mock_requests, mock_api_keys):
        mock_requests.add(
            "GET",
            self.build_url(),
            match_querystring=True,
            json={"id": 0, "word": "commendation"},
        )

        out, _ = self.call()

        expected = "Your random word is \x02commendation\x02."

        assert out == expected
