import pytest


@pytest.mark.parametrize(
    "text,output",
    [
        ("", "No output"),
        ("[", "Unbalanced brackets"),
        ("]", "Unbalanced brackets"),
        (
            "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++.."
            "+++.>>.<-.<.+++.------.--------.>>+.>++.",
            "Hello World!",
        ),
        ("+[>.]+", "No printable output"),
        ("++++[>.]+", "No printable output"),
        ("++++[>++]+.", "(no output)(exceeded 1000000 iterations)"),
        ("++++[>,]+.", "(no output)(exceeded 1000000 iterations)"),
        ("[>,]>+.", "No printable output"),
        (".." * 500, "No printable output"),
    ],
)
def test_brainfuck(text, output):
    from plugins.brainfuck import bf

    assert bf(text) == output
