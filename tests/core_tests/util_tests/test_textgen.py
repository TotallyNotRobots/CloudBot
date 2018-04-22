def test_basic_format():
    from cloudbot.util.textgen import TextGenerator
    generator = TextGenerator(
        ["{test} thing {other} {third}"],
        {"test": ["a", ("b", 10)]},
        [0],
        {"other": "a"}
    )

    generator.generate_strings(100)


def test_get_template():
    from cloudbot.util.textgen import TextGenerator
    generator = TextGenerator(
        ["{test} thing {other} {third}"],
        {"test": ["a", ("b", 10)]},
        [0],
        {"other": "a"}
    )
    assert generator.get_template(0) == "{test} thing {other} {third}"


def test_no_defaults():
    from cloudbot.util.textgen import TextGenerator
    generator = TextGenerator(
        ["{test} thing {other} {third}"],
        {"test": ["a", ("b", 10)]},
        [],
        {"other": "a"}
    )

    generator.generate_strings(100)
