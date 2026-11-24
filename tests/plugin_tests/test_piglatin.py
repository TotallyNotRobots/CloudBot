from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from plugins import piglatin
from tests.util import get_data_path

if TYPE_CHECKING:
    from collections.abc import Generator

TEST_WORDS = {
    "happy": "appyhay",
    "sad": "adsay",
    "test": "esttay",
    "psh": "pshay",
    "fs": "fsay",
}


def load_data() -> None:
    path = get_data_path() / "nltk" / "cmudict.json"
    if path.exists():
        piglatin.pronunciations.update(
            json.loads(path.read_text(encoding="utf-8"))
        )
    else:
        piglatin.load_nltk()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    k: v
                    for k, v in piglatin.pronunciations.items()
                    if k in TEST_WORDS
                }
            ),
            encoding="utf-8",
        )


@pytest.fixture(autouse=True)
def clear_data() -> Generator[None]:
    yield
    piglatin.pronunciations.clear()


@pytest.mark.parametrize(("text", "output"), list(TEST_WORDS.items()))
def test_piglatin(text: str, output: str) -> None:
    load_data()
    assert piglatin.piglatin(text) == output
