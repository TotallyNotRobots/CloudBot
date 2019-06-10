import pytest

from plugins.wordnik import format_attrib


@pytest.mark.parametrize('source,name', [
    ('ahd', 'AHD/Wordnik'),
    ('ahd-5', 'AHD/Wordnik'),
    ('ahd-6', 'Ahd-6/Wordnik'),
    ('foobar', 'Foobar/Wordnik'),
])
def test_attr_name(source, name):
    assert format_attrib(source) == name
