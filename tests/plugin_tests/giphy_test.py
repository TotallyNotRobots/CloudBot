from plugins import giphy


def test_giphy(mock_requests, mock_bot):
    mock_requests.add(
        "GET",
        "http://api.giphy.com/v1/gifs/search?q=foo&limit=10&fmt=json",
        json={"data": [{"rating": None, "embed_url": "foo.bar"}]},
    )
    res = giphy.giphy("foo", mock_bot)
    assert res == "foo.bar - (Powered by GIPHY)"


def test_giphy_rating(mock_requests, mock_bot):
    mock_requests.add(
        "GET",
        "http://api.giphy.com/v1/gifs/search?q=foo&limit=10&fmt=json",
        json={"data": [{"rating": "PG", "embed_url": "foo.bar"}]},
    )
    res = giphy.giphy("foo", mock_bot)
    assert res == "foo.bar content rating: \x02PG\x02. (Powered by GIPHY)"


def test_giphy_no_results(mock_requests, mock_bot):
    mock_requests.add(
        "GET",
        "http://api.giphy.com/v1/gifs/search?q=foo&limit=10&fmt=json",
        json={"data": []},
    )
    res = giphy.giphy("foo", mock_bot)
    assert res == "no results found."
