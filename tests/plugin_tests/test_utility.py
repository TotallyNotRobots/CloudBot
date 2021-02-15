from pathlib import Path

import pytest

from cloudbot.util.http import compare_urls
from plugins import utility

# Defined here because we use the same test cases for unescape
# Except in reverse
ESCAPE_DATA = [
    ("\x00\x01345\x05", r"\x00\x01345\x05"),
]


class MockFunction:
    def __init__(self):
        self.args = []

    def __call__(self, *args, **kwargs):
        self.args.append((args, kwargs))


@pytest.mark.parametrize(
    "a,b,match",
    [
        ("http://example.com/?a=1&b=1", "http://example.com/?b=1&a=1", True),
    ],
)
def test_compare_urls(a, b, match):
    assert compare_urls(a, b) == match


@pytest.mark.parametrize(
    "data,url",
    [
        [
            "foo bar_baz+bing//",
            (
                "http://chart.googleapis.com/chart"
                "?cht=qr&chs=200x200&chl=foo+bar_baz%2Bbing%2F%2F"
            ),
        ],
    ],
)
def test_qrcode(data, url, patch_try_shorten):
    assert compare_urls(utility.qrcode(data), url)


@pytest.mark.parametrize(
    "text,output",
    [
        ("\2foo\2", "foo"),
        ("\x0301,03foo\x0F", "foo"),
    ],
)
def test_strip(text, output):
    assert utility.strip(text) == output


@pytest.mark.parametrize(
    "text,replace,out",
    [
        ("foo", {"f": "br"}, "broo"),
    ],
)
def test_translate(text, replace, out):
    assert utility.translate(text, replace) == out


@pytest.mark.parametrize(
    "text,output",
    [
        ("foo. bar", "Foo. Bar"),
        ("foo. bar. ", "Foo. Bar. "),
    ],
)
def test_capitalize(text, output):
    assert utility.capitalize(text) == output


@pytest.mark.parametrize(
    "text,output",
    [
        ("foo", "FOO"),
        ("foo bar", "FOO BAR"),
        ("Foo", "FOO"),
        ("fOO", "FOO"),
        ("FOO", "FOO"),
    ],
)
def test_upper(text, output):
    assert utility.upper(text) == output


@pytest.mark.parametrize(
    "text,output",
    [
        ("foo", "foo"),
        ("foo bar", "foo bar"),
        ("Foo", "foo"),
        ("fOO", "foo"),
        ("FOO", "foo"),
    ],
)
def test_lower(text, output):
    assert utility.lower(text) == output


@pytest.mark.parametrize(
    "text,output",
    [
        ("foo", "Foo"),
        ("foo bar", "Foo Bar"),
        ("Foo", "Foo"),
        ("fOO", "Foo"),
        ("FOO", "Foo"),
    ],
)
def test_titlecase(text, output):
    assert utility.titlecase(text) == output


@pytest.mark.parametrize(
    "text,output",
    [
        ("foo", "FOO"),
        ("foo bar", "FOO BAR"),
        ("Foo", "fOO"),
        ("fOO", "Foo"),
        ("FOO", "foo"),
    ],
)
def test_swapcase(text, output):
    assert utility.swapcase(text) == output


@pytest.mark.parametrize(
    "text,output",
    [
        ("foo", "ｆｏｏ"),
        ("foo bar", "ｆｏｏ ｂａｒ"),
        ("Foo", "Ｆｏｏ"),
        ("fOO", "ｆＯＯ"),
        ("FOO", "ＦＯＯ"),
    ],
)
def test_fullwidth(text, output):
    assert utility.fullwidth(text) == output


@pytest.mark.parametrize(
    "text,output",
    [
        ("foo", "sbb"),
        ("foo bar", "sbb one"),
        ("Foo", "Sbb"),
        ("fOO", "sBB"),
        ("FOO", "SBB"),
    ],
)
def test_rot13_encode(text, output):
    assert utility.rot13_encode(text) == output


@pytest.mark.parametrize(
    "text,output",
    [
        ("foo", "Zm9v"),
        ("foo bar", "Zm9vIGJhcg=="),
        ("Foo", "Rm9v"),
        ("fOO", "Zk9P"),
        ("FOO", "Rk9P"),
    ],
)
def test_base64_encode(text, output):
    assert utility.base64_encode(text) == output


@pytest.mark.parametrize(
    "text,out",
    [
        ("az", None),
        ("Zm9v", "foo"),
        ("Zm9vIGJhcg==", "foo bar"),
        ("Rm9v", "Foo"),
        ("Zk9P", "fOO"),
        ("Rk9P", "FOO"),
        ("4oSi", "\u2122"),
        [
            "AQ==",
            "Non printable characters detected in output, escaped output: '\\x01'",
        ],
    ],
)
def test_base64_decode(text, out):
    mock_notice = MockFunction()
    ret = utility.base64_decode(text, mock_notice)
    if out is None:
        assert ret is None
        assert len(mock_notice.args) == 1
        assert mock_notice.args[0][0][0] == "Invalid base64 string '{}'".format(
            text
        )
    else:
        assert ret == out


@pytest.mark.parametrize(
    "text,valid",
    [
        ("aa", False),
        ("aaa=", True),
    ],
)
def test_base64_check(text, valid):
    ret = utility.base64_check(text)
    if valid:
        assert ret == "'{}' is a valid base64 encoded string".format(text)
    else:
        assert ret == "'{}' is not a valid base64 encoded string".format(text)


@pytest.mark.parametrize("text,output", ESCAPE_DATA)
def test_escape(text, output):
    assert utility.escape(text) == output


@pytest.mark.parametrize(
    "text,output", [(out, text) for text, out in ESCAPE_DATA]
)
def test_unescape(text, output):
    assert utility.unescape(text) == output


@pytest.mark.parametrize(
    "text,output",
    [
        ("foo", "oof"),
        ("foo bar", "rab oof"),
        ("Foo", "ooF"),
        ("fOO", "OOf"),
        ("FOO", "OOF"),
    ],
)
def test_reverse(text, output):
    assert utility.reverse(text) == output


@pytest.mark.parametrize(
    "text,text_length",
    [
        ("foo", 3),
        ("foo bar", 7),
        ("Foo", 3),
        ("fOO", 3),
        ("FOO", 3),
    ],
)
def test_length(text, text_length):
    assert utility.length(
        text
    ) == "The length of that string is {} characters.".format(text_length)


@pytest.mark.parametrize(
    "text,out",
    [
        ("$(red)foo$(clear)", "\x0304foo\x0F"),
        ("$(bold)foo$(clear)", "\x02foo\x0F"),
    ],
)
def test_color_parse(text, out):
    assert utility.color_parse(text) == out


@pytest.mark.parametrize(
    "text,out",
    [
        ("foobar", "\x0304f\x0307o\x0308o\x0309b\x0303a\x0310r"),
        ("foo bar", "\x0304f\x0307o\x0308o \x0303b\x0310a\x0312r"),
    ],
)
def test_rainbow(text, out):
    assert utility.rainbow(text) == out


@pytest.mark.parametrize(
    "text,out",
    [
        ("foo bar baz", "\x0304foo \x0307bar \x0308baz"),
    ],
)
def test_wrainbow(text, out):
    assert utility.wrainbow(text) == out


@pytest.mark.parametrize(
    "text,out",
    [
        [
            "foo bar baz!",
            (
                "md5: e23f57ae0441216d5c818ba18c1fc98b, "
                "sha1: 0c126b9d298b568656cad2fa1ba679b106b3f5da, "
                "sha256: "
                "6afee6de002d236bd35ea0918848b8f85342acd887499b5e8567598af1e337b4"
            ),
        ],
    ],
)
def test_hash_command(text, out):
    assert utility.hash_command(text) == out


@pytest.fixture()
def leet_data(mock_bot_factory):
    mock_bot = mock_bot_factory(base_dir=Path().resolve())
    utility.load_text(mock_bot)
    yield
    utility.leet_text.clear()


@pytest.mark.parametrize(
    "text",
    [
        "foo bar baz!",
    ],
)
def test_munge(text, leet_data):
    assert utility.munge(text)


@pytest.mark.parametrize(
    "text",
    [
        "foo bar baz!",
    ],
)
def test_leet(text, leet_data):
    assert utility.leet(text)


@pytest.mark.parametrize(
    "text",
    [
        "foo bar baz!",
    ],
)
def test_derpify(text):
    assert utility.derpify(text)


@pytest.mark.parametrize(
    "text,out",
    [
        [
            "foo bar baz!",
            (
                "\x0304f\x0300o\x0302o\x0304 "
                "\x0300b\x0302a\x0304r\x0300 "
                "\x0302b\x0304a\x0300z\x0302!"
            ),
        ],
    ],
)
def test_usa(text, out):
    assert utility.usa(text) == out


@pytest.mark.parametrize(
    "text,out",
    [
        ("foo bar baz!", "ᶠᵒᵒ ᵇᵃʳ ᵇᵃᶻ!"),
    ],
)
def test_superscript(text, out):
    assert utility.superscript(text) == out
