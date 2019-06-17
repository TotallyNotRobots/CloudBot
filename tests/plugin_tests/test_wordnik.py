import pytest
from mock import MagicMock
from responses import RequestsMock

from cloudbot.bot import bot
from plugins import wordnik


@pytest.fixture()
def mock_requests():
    with RequestsMock() as reqs:
        yield reqs


@pytest.fixture()
def mock_api_keys():
    try:
        bot.set(MagicMock())
        bot.config.get_api_key.return_value = "APIKEY"
        yield bot.config.get_api_key
    finally:
        bot.set(None)


@pytest.mark.parametrize('source,name', [
    ('ahd', 'AHD/Wordnik'),
    ('ahd-5', 'AHD/Wordnik'),
    ('ahd-6', 'Ahd-6/Wordnik'),
    ('foobar', 'Foobar/Wordnik'),
])
def test_attr_name(source, name):
    assert wordnik.format_attrib(source) == name


def test_no_api_key(mock_requests, mock_api_keys):
    from plugins import wordnik

    mock_api_keys.return_value = None

    mock_event = MagicMock()

    with pytest.raises(wordnik.NoAPIKey):
        wordnik.define('word', mock_event)

    mock_event.reply.assert_called_with(
        'There was a problem contacting the Wordnik API '
        '(This command requires an API key from wordnik.com.)'
    )


class TestDefine:
    func = wordnik.define

    def call(self, text, event=None):
        if event is None:
            event = MagicMock()

        return self.func(text, event), event

    def test_not_found(self, mock_requests, mock_api_keys):
        mock_requests.add(
            'GET',
            'http://api.wordnik.com/v4/word.json/word/definitions'
            '?limit=1&api_key=APIKEY',
            match_querystring=True,
            status=404,
            json={'error': "Not Found"},
        )

        expected = "I could not find a definition for \x02word\x02."

        out, _ = self.call('word')
        assert out == expected

    def test_search(self, mock_requests, mock_api_keys):
        mock_requests.add(
            'GET',
            'http://api.wordnik.com/v4/word.json/word/definitions'
            '?limit=1&api_key=APIKEY',
            match_querystring=True,
            json=[{
                "id": "W5229000-1",
                "partOfSpeech": "noun",
                "attributionText": "from The American Heritage® Dictionary of the "
                                   "English Language, 5th Edition.",
                "sourceDictionary": "ahd-5",
                "text": "A sound or a combination of sounds, or its "
                        "representation in writing or printing, that symbolizes "
                        "and communicates a meaning and may consist of a single "
                        "morpheme or of a combination of morphemes.",
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
                "wordnikUrl": "https://www.wordnik.com/words/word"
            }],
        )

        expected = "\x02word\x02: A sound or a combination of sounds, or its " \
                   "representation in writing or printing, that symbolizes and " \
                   "communicates a meaning and may consist of a single morpheme " \
                   "or of a combination of morphemes. " \
                   "- https://www.wordnik.com/words/word (AHD/Wordnik)"

        out, _ = self.call('word')
        assert out == expected
