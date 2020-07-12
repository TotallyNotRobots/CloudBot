from unittest.mock import MagicMock

from cloudbot.event import CommandEvent
from plugins import quran
from tests.util import wrap_hook_response


def test_quran(mock_requests):
    event = CommandEvent(
        channel="#foo",
        text="1:1",
        triggered_command="quran",
        cmd_prefix=".",
        hook=MagicMock(),
        conn=MagicMock(),
    )
    mock_requests.add(
        "GET",
        "http://quranapi.azurewebsites.net/api/verse/?chapter=1&number=1&lang"
        "=ar",
        json={
            "Id": 1,
            "Chapter": 1,
            "ChapterName": "الفَاتِحَة",
            "Text": "ٱلۡحَمۡدُ لِلَّهِ رَبِّ ٱلۡعَـٰلَمِينَ",
            "ISO1Code": "ar",
            "Description": "Auto added at '3/4/2013 11:44:36 PM'.",
            "TransId": 0,
            "ScriptId": 1,
        },
        match_querystring=True,
    )
    mock_requests.add(
        "GET",
        "http://quranapi.azurewebsites.net/api/verse/"
        "?chapter=1&number=1&lang=en",
        json={
            "Id": 1,
            "Chapter": 1,
            "ChapterName": "Al-Fatiha",
            "Text": "Praise be to Allah, Lord of the Worlds,",
            "ISO1Code": "en",
            "Description": "Auto added at '3/6/2013 12:19:00 PM'.",
            "TransId": 3,
            "ScriptId": 1,
        },
        match_querystring=True,
    )
    res = wrap_hook_response(quran.quran, event)
    assert res == [
        (
            "message",
            ("#foo", "\x021:1\x02: ٱلۡحَمۡدُ لِلَّهِ رَبِّ ٱلۡعَـٰلَمِينَ"),
        ),
        ("return", "Praise be to Allah, Lord of the Worlds,"),
    ]
