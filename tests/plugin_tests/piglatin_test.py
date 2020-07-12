import pytest

from plugins import piglatin


@pytest.fixture()
def load_data():
    piglatin.load_nltk()


@pytest.fixture()
def load_no_data():
    piglatin.pronunciations = {None: 1}


def test_missing_data():
    piglatin.pronunciations.clear()
    assert piglatin.piglatin("") == "Please wait, getting NLTK ready!"


DATA = [
    ("foo bar baz hi", "oofay arbay azbay ihay"),
    ("scram", "amscray"),
    ("", ""),
    ("SCRAM", "AMSCRAY"),
    ("SCRAM!", "AMSCRAY!"),
    ("Scram!", "Amscray!"),
    ("b", "bay"),
    ("a", "away"),
    ("allow", "allowway"),
    ("fs", "fsay"),
    ("yellow", "ellowyay"),
]


@pytest.mark.parametrize("text,output", DATA)
def test_piglatin(load_data, text, output):
    assert piglatin.piglatin(text) == output


@pytest.mark.parametrize("text,output", DATA)
def test_basic(load_no_data, text, output):
    assert piglatin.piglatin(text) == output
