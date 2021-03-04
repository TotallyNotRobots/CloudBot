from unittest.mock import MagicMock, call

from plugins import drinks


def test_drinks_no_recipe(patch_try_shorten):
    drinks.drink_data.clear()
    drinks.drink_data.append(
        {"title": "foobar", "url": "foo.bar", "ingredients": ["foo", "bar"]}
    )

    event = MagicMock()
    action = event.action
    text = "foo"
    chan = "#bar"
    res = drinks.drink_cmd(text, chan, action)
    assert res is None
    assert event.mock_calls == [
        call.action(
            "grabs some foo and bar\x0f and makes foo a \x02foobar\x02. foo.bar",
            "#bar",
        )
    ]
