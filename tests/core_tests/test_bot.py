from collections.abc import Mapping

import pytest


@pytest.mark.parametrize(
    "name,cleaned",
    [
        ("AAAAA", "AAAAA"),
        ("AaA12_sF", "AaA12_sF"),
        ("sekDjf fjNs", "sekDjf_fjNs"),
        ("jk .", "jk_"),
    ]
)
def test_clean_name(name, cleaned):
    from cloudbot.bot import clean_name
    assert cleaned == clean_name(name)


class MockObject:
    @classmethod
    def from_dict(cls, d):
        obj = cls()
        for key, value in d.items():
            obj.add_attr(key, value)

        return obj

    @classmethod
    def _wrap(cls, value):
        if isinstance(value, list):
            return [cls._wrap(item) for item in value]

        if isinstance(value, dict):
            return cls.from_dict(value)

        if isinstance(value, MockDict):
            return dict(value)

        return value

    def add_attr(self, name, value):
        setattr(self, name, self._wrap(value))


class MockDict(Mapping):
    def __init__(self, *args, **kwargs):
        self._data = dict(*args, **kwargs)

    def __getitem__(self, item):
        return self._data[item]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


def make_config(client_nick, event_nick, channel, cmd_prefix):
    return MockObject.from_dict({
        "nick": event_nick,
        "chan": channel,
        "conn": {
            "config": MockDict(command_prefix=cmd_prefix),
            "nick": client_nick
        }
    })


@pytest.mark.parametrize("event,text,parts", [
    (
        make_config("testnick", "user", "#chan", "."),
        ".test thing stuff",
        {"prefix": ".", "command": "test", "text": "thing stuff"}
    ),
    (
        make_config("testnick", "user", "#chan", "."),
        "testnick: test thing stuff",
        {"prefix": None, "command": "test", "text": "thing stuff"}
    ),
    (
        make_config("testnick", "user", "user", "."),
        "test thing stuff",
        {"prefix": None, "command": "test", "text": "thing stuff"}
    ),
])
def test_command_regex(event, text, parts):
    from cloudbot.bot import get_cmd_regex

    match = get_cmd_regex(event).match(text)

    for key in parts:
        assert parts[key] == match.group(key)
