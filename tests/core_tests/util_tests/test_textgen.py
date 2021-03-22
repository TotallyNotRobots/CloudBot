import re

from cloudbot.util import textgen


def test_textgenerator():
    generator = textgen.TextGenerator(
        ["{thing} is {stuff}"],
        {
            "thing": ["a", "b"],
            "stuff": [
                "c",
                ("d", 2),
            ],
        },
    )

    for s in generator.generate_strings(4):
        assert re.match(r"[ab] is [cd]", s)

    assert generator.get_template(0) == "{thing} is {stuff}"


def test_textgen_default_tmpl():
    generator = textgen.TextGenerator(
        [
            "{thing} is {stuff} {a}",
            "{thing} are {stuff} {a}",
        ],
        {
            "thing": ["a", "b"],
            "stuff": [
                "c",
                ("d", 2),
            ],
        },
        default_templates=[1],
        variables={"a": "foo"},
    )

    for s in generator.generate_strings(4):
        assert re.match(r"[ab] are [cd] foo", s)

    assert generator.get_template(0) == "{thing} is {stuff} {a}"
    assert generator.get_template(1) == "{thing} are {stuff} {a}"
