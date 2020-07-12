from unittest.mock import MagicMock

from plugins import google_translate


def test_translate(mock_requests, mock_api_keys):
    mock_requests.add(
        "POST",
        "https://www.googleapis.com/language/translate/v2",
        json={
            "data": {
                "translations": [
                    {"detectedSourceLanguage": "es", "translatedText": "Hello",}
                ]
            }
        },
    )
    reply = MagicMock()
    res = google_translate.translate("hola", reply)
    assert res == "(es) Hello"
    assert reply.mock_calls == []
