import pytest


@pytest.mark.parametrize('text,item_type,item_id', [
    ('open.spotify.com/user/foobar', 'user', 'foobar'),
])
def test_http_re(text, item_type, item_id):
    from plugins.spotify import http_re
    match = http_re.search(text)
    assert match and match.group(2) == item_type and match.group(3) == item_id


@pytest.mark.parametrize('text,item_type,item_id', [
    ('spotify:user:foobar', 'user', 'foobar'),
])
def test_spotify_re(text, item_type, item_id):
    from plugins.spotify import spotify_re
    match = spotify_re.search(text)
    assert match and match.group(2) == item_type and match.group(3) == item_id


@pytest.mark.parametrize('data,item_type,output', [
    (
        {
            'display_name': 'linuxdaemon',
            'external_urls': {
                'spotify': 'https://open.spotify.com/user/7777'
            },
            'followers': {
                'total': 2500
            },
            'uri': 'spotify:user:7777'
        },
        'user',
        '\x02linuxdaemon\x02, Followers: \x022,500\x02'
    ),
    (
        {
            'name': 'foobar',
            'artists': [
                {'name': 'FooBar'}
            ],
            'album': {
                'name': 'Baz'
            }
        },
        'track',
        '\x02foobar\x02 by \x02FooBar\x02 from the album \x02Baz\x02',
    ),
])
def test_format_response(data, item_type, output):
    from plugins.spotify import _format_response
    assert _format_response(data, item_type) == output
