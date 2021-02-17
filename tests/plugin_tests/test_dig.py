def test_dig():
    from plugins import dig

    s = "The jsondns API no longer exists. This command is retired."
    assert dig.dig() == s
