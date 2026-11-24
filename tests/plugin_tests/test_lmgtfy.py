import pytest

from plugins import lmgtfy


@pytest.mark.usefixtures("patch_try_shorten")
def test_lmgtfy() -> None:
    assert lmgtfy.lmgtfy("foo bar") == "http://lmgtfy.com/?q=foo%20bar"
