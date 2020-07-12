import pytest

from plugins import imdb


@pytest.mark.parametrize(
    "text,out",
    [
        ("https://www.imdb.com/title/tt1950186/", "tt1950186"),
        (
            "https://www.imdb.com/title/tt2575988/mediaviewer/rm668743424"
            "?ft0=name&fv0=nm1476909&ft1=image_type&fv1=still_frame",
            "tt2575988",
        ),
        ("http://www.imdb.com/title/tt1950186/", "tt1950186"),
        (
            "http://www.imdb.com/title/tt2575988/mediaviewer/rm668743424"
            "?ft0=name&fv0=nm1476909&ft1=image_type&fv1=still_frame",
            "tt2575988",
        ),
        ("https://imdb.com/title/tt1950186/", "tt1950186"),
        (
            "https://imdb.com/title/tt2575988/mediaviewer/rm668743424"
            "?ft0=name&fv0=nm1476909&ft1=image_type&fv1=still_frame",
            "tt2575988",
        ),
        ("http://imdb.com/title/tt1950186/", "tt1950186"),
        (
            "http://imdb.com/title/tt2575988/mediaviewer/rm668743424"
            "?ft0=name&fv0=nm1476909&ft1=image_type&fv1=still_frame",
            "tt2575988",
        ),
        ("https://www.imdb.com/title/tt1950186", "tt1950186"),
        ("http://www.imdb.com/title/tt1950186", "tt1950186"),
        ("https://imdb.com/title/tt1950186", "tt1950186"),
        ("http://imdb.com/title/tt1950186", "tt1950186"),
        ("http://www.imdb.com/title/stuff", None),
    ],
)
def test_imdb_re(text, out):
    res = imdb.imdb_re.match(text)
    if out is None:
        assert not res
    else:
        assert res.group(1) == out


@pytest.mark.parametrize(
    "data,out",
    [
        (
            {
                "id": "tt1950186",
                "title": "Ford v Ferrari",
                "year": "2019",
                "genres": [],
                "plot": "American car designer Carroll Shelby and driver Ken "
                "Miles battle corporate interference, the laws of "
                "physics and their own personal demons to build a "
                "revolutionary race car for Ford and challenge "
                "Ferrari at the 24 Hours of Le Mans in 1966.",
                "runtime": "2h 32min",
                "rating": "8.3",
                "votes": "39746",
                "photoUrl": "https://m.media-amazon.com/images/M"
                "/MV5BYzcyZDNlNDktOWRhYy00ODQ5LTg1ODQ"
                "tZmFmZTIyMjg2Yjk5XkEyXkFqcGdeQXVyMTkx"
                "NjUyNQ@@._V1_UX182_CR0,0,182,268_AL_.jpg",
                "directors": [],
                "writers": [],
                "stars": [],
                "retrieved": "2019-11-29T10:29:06.009Z",
            },
            (
                "\x02Ford v Ferrari\x02 (2019) (): American car designer "
                "Carroll Shelby and driver Ken Miles battle corporate "
                "interference, the laws of physics and their own personal "
                "demons to build a revolutionary race car for Ford and "
                "challenge Ferrari at the 24 Hours of Le Mans in 1966. \x022h "
                "32min\x02. \x028.3/10\x02 with \x0239746\x02 votes."
            ),
        ),
        (
            {
                "genres": [],
                "runtime": "N/A",
                "rating": "N/A",
                "votes": "N/A",
                "title": "foo",
                "year": 2020,
                "plot": "foobar",
            },
            "\x02foo\x02 (2020) (): foobar",
        ),
    ],
)
def test_movie_str(data, out):
    assert imdb.movie_str(data) == out
