import pytest

test_input = "The quick $(brown, red)brown$(clear) fox$(fake) jumps over the $(bold)lazy dog$(clear)."

test_parse_output = "The quick \x0305,04brown\x0f fox jumps over the \x02lazy dog\x0f."
test_strip_output = "The quick brown fox jumps over the lazy dog."

test_strip_irc_input = "\x02I am $(bold)bold\x02"
test_strip_irc_result = "I am $(bold)bold"
test_strip_all_result = "I am bold"


def test_parse():
    from cloudbot.util.colors import parse
    assert parse(test_input) == test_parse_output


def test_strip():
    from cloudbot.util.colors import strip, strip_irc, strip_all
    assert strip(test_input) == test_strip_output
    assert strip_irc(test_strip_irc_input) == test_strip_irc_result
    assert strip_all(test_strip_irc_input) == test_strip_all_result


def test_available_colors():
    from cloudbot.util.colors import get_available_colours
    assert "dark_grey" in get_available_colours()


def test_available_formats():
    from cloudbot.util.colors import get_available_formats
    assert "bold" in get_available_formats()


def test_invalid_color():
    from cloudbot.util.colors import get_color
    with pytest.raises(KeyError) as excinfo:
        get_color("cake")
    assert 'not in the list of available colours' in str(excinfo.value)


def test_invalid_format():
    from cloudbot.util.colors import get_format
    with pytest.raises(KeyError) as excinfo:
        get_format("cake")
    assert 'not found in the list of available formats' in str(excinfo.value)


def test_get_color():
    from cloudbot.util.colors import get_color
    assert get_color("red") == "\x0304"
    assert get_color("red", return_formatted=False) == "04"


def test_get_random_color():
    from cloudbot.util.colors import get_color, IRC_COLOUR_DICT
    assert get_color("random") in ["\x03" + i for i in IRC_COLOUR_DICT.values()]
    assert get_color("random", return_formatted=False) in list(IRC_COLOUR_DICT.values())


def test_get_format():
    from cloudbot.util.colors import get_format
    assert get_format("bold") == "\x02"


def test_convert():
    from cloudbot.util.colors import _convert
    assert _convert("$(red, green)") == "\x0304,09"
    assert _convert("$(red, bold)") == "\x0304\x02"
    assert _convert("$(red)") == "\x0304"
    assert _convert("$(bold)") == "\x02"
    assert _convert("cats") == "cats"
