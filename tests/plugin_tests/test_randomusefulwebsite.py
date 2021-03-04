def test_random_useful_site(mock_requests):
    mock_requests.add(
        mock_requests.HEAD,
        "http://www.discuvver.com/jump2.php",
        adding_headers={"Location": "http://example.com/"},
        status=301,
    )
    mock_requests.add(mock_requests.HEAD, "http://example.com/")
    from plugins.randomusefulwebsites import randomusefulwebsite

    assert randomusefulwebsite() == "http://example.com/"
