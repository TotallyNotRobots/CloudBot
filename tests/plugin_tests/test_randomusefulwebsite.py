from responses import RequestsMock


def test_random_useful_site():
    with RequestsMock() as reqs:
        reqs.add(
            reqs.HEAD, 'http://www.discuvver.com/jump2.php',
            adding_headers={
                'Location': 'http://example.com/'
            },
            status=301
        )
        reqs.add(reqs.HEAD, 'http://example.com/')
        from plugins.randomusefulwebsites import randomusefulwebsite
        assert randomusefulwebsite() == 'http://example.com/'
