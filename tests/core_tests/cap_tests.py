from cloudbot.clients.irc.parser import Cap
from plugins.core.cap import ServerCaps


def test_cap_compare():
    caps = ServerCaps()
    test_cap_name = "test-cap-thing"
    test_cap = Cap.parse(test_cap_name)
    assert test_cap == test_cap_name
    assert test_cap_name == test_cap

    caps.enabled.add(test_cap)

    assert caps.is_cap_enabled(test_cap)
    assert caps.is_cap_enabled(Cap.parse(test_cap_name))
    assert caps.is_cap_enabled(test_cap_name)
