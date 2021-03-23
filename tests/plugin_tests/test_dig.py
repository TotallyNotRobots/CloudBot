from plugins import dig


def test_dig():
    s = "The jsondns API no longer exists. This command is retired."
    assert dig.dig() == s
