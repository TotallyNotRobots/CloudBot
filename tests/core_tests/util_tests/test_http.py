from unittest.mock import patch


def test_get_soup():
    test_data = """
    <html>
        <body>
            <div class="thing"><p>foobar</p></div>
        </body>
    </html>
    """
    with patch('cloudbot.util.http.get', lambda *a, **k: test_data):
        from cloudbot.util import http
        soup = http.get_soup('http://example.com')
        assert soup.find('div', {'class': "thing"}).p.text == "foobar"
