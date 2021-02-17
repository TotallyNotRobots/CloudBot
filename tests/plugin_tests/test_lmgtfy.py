def test_lmgtfy(patch_try_shorten):
    from plugins.lmgtfy import lmgtfy

    assert lmgtfy("foo bar") == "http://lmgtfy.com/?q=foo%20bar"
