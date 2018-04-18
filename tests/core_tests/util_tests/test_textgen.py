def test_basic_format():
    from cloudbot.util.textgen import TextGenerator
    generator = TextGenerator(
        ["{test} thing {other} {third}"],
        {"test": ["a", ("b", 10)]},
        [0],
        {"other": "a"}
    )

    generator.generate_strings(100)
