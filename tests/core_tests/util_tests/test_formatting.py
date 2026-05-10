from textwrap import dedent

import pytest

from cloudbot.util.formatting import (
    chunk_str,
    dict_format,
    gen_markdown_table,
    get_text_list,
    ireplace,
    multi_replace,
    multiword_replace,
    munge,
    pluralize_auto,
    pluralize_suffix,
    smart_split,
    strip_colors,
    strip_html,
    truncate,
    truncate_str,
    truncate_words,
)

test_munge_input = "The quick brown fox jumps over the lazy dog"
test_munge_count = 3
test_munge_result_a = "\u0162\u0127\xeb \u02a0\xfc\xed\u010b\u0137 \u0411\u0157\xf6\u03c9\xf1 \u0192\xf6\u03c7 \u0135\xfc\u1e41\u03c1\u0161 \xf6v\xeb\u0157 \u0163\u0127\xeb \u013a\xe4\u017a\xff \u0111\xf6\u0121"
test_munge_result_b = "\u0162\u0127\xeb quick brown fox jumps over the lazy dog"

test_format_formats = ["{a} {b} {c}", "{a} {b}", "{a}"]
test_format_data = {"a": "First Thing", "b": "Second Thing"}
test_format_result = "First Thing Second Thing"

test_pluralize_num_a = 1
test_pluralize_num_b = 5
test_pluralize_result_a = "1 cake"
test_pluralize_result_b = "5 cakes"
test_pluralize_text = "cake"

test_strip_colors_input = "\x02I am bold\x02"
test_strip_colors_result = "I am bold"

test_truncate_str_input = "I am the example string for a unit test"
test_truncate_str_length_a = 10
test_truncate_str_length_b = 100
test_truncate_str_result_a = "I am the..."
test_truncate_str_result_b = "I am the example string for a unit test"

test_truncate_words_input = "I am the example string for a unit test"
test_truncate_words_length_a = 5
test_truncate_words_length_b = 100
test_truncate_words_result_a = "I am the example string..."
test_truncate_words_result_b = "I am the example string for a unit test"

test_strip_html_input = "<strong>Cats &amp; Dogs: &#181;</strong>"
test_strip_html_result = "Cats & Dogs: \xb5"

test_multiword_replace_dict = {"<bit1>": "<replace1>", "[bit2]": "[replace2]"}
test_multiword_replace_text = "<bit1> likes [bit2]"
test_multiword_replace_result = "<replace1> likes [replace2]"

test_ireplace_input = "The quick brown FOX fox FOX jumped over the lazy dog"

test_chunk_str_input = "The quick brown fox jumped over the lazy dog"
test_chunk_str_result = [
    "The quick",
    "brown fox",
    "jumped",
    "over the",
    "lazy dog",
]


def test_munge() -> None:
    assert munge(test_munge_input) == test_munge_result_a
    assert munge(test_munge_input, test_munge_count) == test_munge_result_b


def test_dict_format() -> None:
    assert (
        dict_format(test_format_data, test_format_formats) == test_format_result
    )
    assert dict_format({}, test_format_formats) is None


def test_pluralize() -> None:
    assert (
        pluralize_suffix(test_pluralize_num_a, test_pluralize_text)
        == test_pluralize_result_a
    )
    assert (
        pluralize_suffix(test_pluralize_num_b, test_pluralize_text)
        == test_pluralize_result_b
    )


@pytest.mark.parametrize(
    "item,count,output",
    [
        ("foo", 1, "1 foo"),
        ("bar", 2, "2 bars"),
        ("foos", 2, "2 fooses"),
        ("leaf", 2, "2 leaves"),
        ("city", 2, "2 cities"),
        ("day", 2, "2 days"),
        ("foe", 2, "2 foes"),
        ("volcano", 2, "2 volcanoes"),
        ("radius", 2, "2 radii"),
        ("hoof", 2, "2 hooves"),
        ("axis", 2, "2 axes"),
        ("automaton", 2, "2 automata"),
        ("tree", 2, "2 trees"),
    ],
)
def test_auto_pluralize(item, count, output) -> None:
    assert pluralize_auto(count, item) == output


def test_strip_colors() -> None:
    # compatibility
    assert strip_colors(test_strip_colors_input) == test_strip_colors_result


def test_truncate_str() -> None:
    assert (
        truncate(test_truncate_str_input, length=test_truncate_str_length_a)
        == test_truncate_str_result_a
    )
    assert (
        truncate(test_truncate_str_input, length=test_truncate_str_length_b)
        == test_truncate_str_result_b
    )

    # compatibility
    assert (
        truncate_str(test_truncate_str_input, length=test_truncate_str_length_a)
        == test_truncate_str_result_a
    )
    assert (
        truncate_str(test_truncate_str_input, length=test_truncate_str_length_b)
        == test_truncate_str_result_b
    )


def test_truncate_words() -> None:
    assert (
        truncate_words(
            test_truncate_words_input, length=test_truncate_words_length_a
        )
        == test_truncate_words_result_a
    )
    assert (
        truncate_words(
            test_truncate_words_input, length=test_truncate_words_length_b
        )
        == test_truncate_words_result_b
    )


def test_strip_html() -> None:
    assert strip_html(test_strip_html_input) == test_strip_html_result


def test_multiword_replace() -> None:
    assert (
        multi_replace(test_multiword_replace_text, test_multiword_replace_dict)
        == test_multiword_replace_result
    )

    # compatibility
    assert (
        multiword_replace(
            test_multiword_replace_text, test_multiword_replace_dict
        )
        == test_multiword_replace_result
    )


def test_ireplace() -> None:
    assert (
        ireplace(test_ireplace_input, "fox", "cat")
        == "The quick brown cat cat cat jumped over the lazy dog"
    )
    assert (
        ireplace(test_ireplace_input, "FOX", "cAt")
        == "The quick brown cAt cAt cAt jumped over the lazy dog"
    )
    assert (
        ireplace(test_ireplace_input, "fox", "cat", 1)
        == "The quick brown cat fox FOX jumped over the lazy dog"
    )
    assert (
        ireplace(test_ireplace_input, "fox", "cat", 2)
        == "The quick brown cat cat FOX jumped over the lazy dog"
    )

    # test blank input - this should behave like the native string.replace()
    assert ireplace("Hello", "", "?") == "?H?e?l?l?o?"


def test_chunk_str() -> None:
    assert chunk_str(test_chunk_str_input, 10) == test_chunk_str_result


def test_get_text_list() -> None:
    assert get_text_list(["a", "b", "c", "d"]) == "a, b, c or d"
    assert get_text_list(["a", "b", "c"], "and") == "a, b and c"
    assert get_text_list(["a", "b"], "and") == "a and b"
    assert get_text_list(["a"]) == "a"
    assert get_text_list([]) == ""


def test_smart_split() -> None:
    assert list(smart_split(r'This is "a person\'s" test.')) == [
        "This",
        "is",
        '"a person\\\'s"',
        "test.",
    ]
    assert list(smart_split(r"Another 'person\'s' test.")) == [
        "Another",
        "'person\\'s'",
        "test.",
    ]
    assert list(smart_split(r'A "\"funky\" style" test.')) == [
        "A",
        '"\\"funky\\" style"',
        "test.",
    ]


def test_gen_md_table() -> None:
    headers = ["ColumnA", "Column B"]
    data = [
        ["1", "2"],
        ["3", "4"],
    ]
    expected = """
    | ColumnA | Column B |
    | ------- | -------- |
    | 1       | 2        |
    | 3       | 4        |
    """

    assert gen_markdown_table(headers, data) == dedent(expected).strip()
