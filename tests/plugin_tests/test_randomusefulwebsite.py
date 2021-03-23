from plugins import randomusefulwebsites


def test_random_useful_site(mock_requests):
    mock_requests.add(
        "HEAD",
        "http://www.discuvver.com/jump2.php",
        adding_headers={"Location": "http://example.com/"},
        status=301,
    )
    mock_requests.add("HEAD", "http://example.com/")
    assert randomusefulwebsites.randomusefulwebsite() == "http://example.com/"
