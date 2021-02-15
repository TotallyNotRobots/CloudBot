import pytest

from plugins import imdb


def test_imdb(mock_requests, mock_bot):
    mock_requests.add(
        "GET",
        "https://imdb-scraper.herokuapp.com/search?q=foobar&limit=1",
        json={
            "success": True,
            "result": [
                {
                    "id": "beep",
                    "genres": ["foo", "bar"],
                    "runtime": "N/A",
                    "rating": "N/A",
                    "title": "movie title",
                    "year": 2019,
                    "plot": "Movie plot thing",
                }
            ],
        },
    )
    res = imdb.imdb("foobar", mock_bot)
    assert res == (
        "\x02movie title\x02 (2019) (foo, bar): Movie plot thing "
        "http://www.imdb.com/title/beep"
    )


def test_imdb_failed(mock_requests, mock_bot):
    title_id = "tt123"
    mock_requests.add(
        "GET",
        f"https://imdb-scraper.herokuapp.com/title?id={title_id}",
        json={"success": False},
    )
    res = imdb.imdb(title_id, mock_bot)
    assert res == "Unknown error"


def test_imdb_no_movies(mock_requests, mock_bot):
    title_id = "foo"
    mock_requests.add(
        "GET",
        "https://imdb-scraper.herokuapp.com/search?q=foo&limit=1",
        json={"success": True, "result": []},
    )
    res = imdb.imdb(title_id, mock_bot)
    assert res == "No movie found"


def test_imdb_id(mock_requests, mock_bot):
    title_id = "tt123"
    mock_requests.add(
        "GET",
        f"https://imdb-scraper.herokuapp.com/title?id={title_id}",
        json={
            "success": True,
            "result": {
                "id": "beep",
                "genres": ["foo", "bar"],
                "runtime": "N/A",
                "rating": "N/A",
                "title": "movie title",
                "year": 2019,
                "plot": "Movie plot thing",
            },
        },
    )
    res = imdb.imdb(title_id, mock_bot)
    assert res == (
        "\x02movie title\x02 (2019) (foo, bar): Movie plot thing "
        "http://www.imdb.com/title/beep"
    )


def test_imdb_url_fail(mock_requests, mock_bot):
    match = imdb.imdb_re.search("https://imdb.com/title/tt123")
    title_id = "tt123"
    mock_requests.add(
        "GET",
        f"https://imdb-scraper.herokuapp.com/title?id={title_id}",
        json={
            "success": False,
        },
    )
    res = imdb.imdb_url(match, mock_bot)
    assert res is None


def test_imdb_url(mock_requests, mock_bot):
    match = imdb.imdb_re.search("https://imdb.com/title/tt123")
    title_id = "tt123"
    mock_requests.add(
        "GET",
        f"https://imdb-scraper.herokuapp.com/title?id={title_id}",
        json={
            "success": True,
            "result": {
                "id": "beep",
                "genres": ["foo", "bar"],
                "runtime": "N/A",
                "rating": "N/A",
                "title": "movie title",
                "year": 2019,
                "plot": "Movie plot thing",
            },
        },
    )
    res = imdb.imdb_url(match, mock_bot)
    assert res == "\x02movie title\x02 (2019) (foo, bar): Movie plot thing"


@pytest.mark.parametrize(
    "runtime,rating,votes,out",
    [
        ("N/A", "N/A", "N/A", "\x02foo\x02 (2019) (foo, bar): A movie plot"),
        (
            "1h30m",
            "N/A",
            "N/A",
            "\x02foo\x02 (2019) (foo, bar): A movie plot \x021h30m\x02.",
        ),
        (
            "1h30m",
            "3.5",
            "N/A",
            "\x02foo\x02 (2019) (foo, bar): A movie plot \x021h30m\x02.",
        ),
        (
            "1h30m",
            "N/A",
            "158",
            "\x02foo\x02 (2019) (foo, bar): A movie plot \x021h30m\x02.",
        ),
        (
            "1h30m",
            "3.5",
            "158",
            (
                "\x02foo\x02 (2019) (foo, bar): A movie plot \x021h30m\x02. \x023.5/10\x02 "
                "with \x02158\x02 votes."
            ),
        ),
    ],
)
def test_movie_str(runtime, rating, votes, out):
    movie = {
        "genres": ["foo", "bar"],
        "runtime": runtime,
        "rating": rating,
        "votes": votes,
        "title": "foo",
        "year": "2019",
        "plot": "A movie plot",
    }
    assert imdb.movie_str(movie) == out
