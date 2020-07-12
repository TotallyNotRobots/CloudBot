from unittest.mock import MagicMock

import pytest

from plugins import cypher


@pytest.mark.parametrize(
    "plaintext,key,ciphertext",
    [
        ("some input", "supersecretkey", "w6bDpMOdw4rCksOcw5PDk8Onw5k="),
        (
            "other input and stuff",
            "supersecretkey234",
            "w6LDqcOYw4rDpMKTw47DkcOiw5rDqMKLw4bDp8KWU8Knw6fDqsOWw4s=",
        ),
    ],
)
def test_encipher(plaintext, key, ciphertext):
    event = MagicMock()
    assert cypher.cypher("{} {}".format(key, plaintext), event) == ciphertext


@pytest.mark.parametrize(
    "ciphertext,key,plaintext",
    [
        ("w6bDpMOdw4rCksOcw5PDk8Onw5k=", "supersecretkey", "some input"),
        (
            "w6LDqcOYw4rDpMKTw47DkcOiw5rDqMKLw4bDp8KWU8Knw6fDqsOWw4s=",
            "supersecretkey234",
            "other input and stuff",
        ),
    ],
)
def test_decipher(ciphertext, key, plaintext):
    event = MagicMock()
    assert cypher.decypher("{} {}".format(key, ciphertext), event) == plaintext


def test_base64_error():
    event = MagicMock()
    assert cypher.decypher("thing stuff and things", event) is None

    event.notice.assert_called_with("Invalid input 'stuff and things'")


def test_encipher_param_error():
    event = MagicMock()
    assert cypher.cypher("", event) is None

    assert event.notice_doc.call_count == 1


def test_decipher_param_error():
    event = MagicMock()
    assert cypher.decypher("", event) is None

    assert event.notice_doc.call_count == 1
