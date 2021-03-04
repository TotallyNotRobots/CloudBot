import datetime
import json
from pathlib import Path

import pytest

from plugins import xkcd

DATA_PATH = Path().resolve() / "tests" / "data" / "xkcd"


def get_files():
    for file in DATA_PATH.rglob("*.json"):
        yield int(file.stem)


def load_data(xkcd_id):
    file = DATA_PATH / "{}.json".format(xkcd_id)

    with file.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("xkcd_id", list(get_files()))
def test_info(xkcd_id, mock_requests):
    data = load_data(xkcd_id)
    mock_requests.add(
        "GET",
        "http://www.xkcd.com/{}/info.0.json".format(xkcd_id),
        json=data,
    )

    date = datetime.date(
        year=int(data["year"]),
        month=int(data["month"]),
        day=int(data["day"]),
    )

    no_url = "xkcd: \x02{}\x02 ({:%d %B %Y})".format(data["title"], date)

    with_url = no_url + " | http://www.xkcd.com/{}".format(xkcd_id)

    assert xkcd.xkcd_info(str(xkcd_id)) == no_url
    assert xkcd.xkcd_info(str(xkcd_id), True) == with_url


def test_search(mock_requests):
    mock_requests.add(
        "GET",
        "http://www.ohnorobot.com/?s=foo&Search=Search&comic=56&e=0&n=0&b=0&m=0&d=0&t=0",
        body="""
        <li>
        <div class="tinylink">
            https://xkcd.com/45
        </div>
        </li>
        """,
    )

    mock_requests.add(
        "GET",
        "http://www.xkcd.com/45%0A%20%20%20%20%20%20%20/info.0.json",
        json={"year": 2020, "month": 8, "day": 7, "title": "test title"},
    )

    assert xkcd.xkcd("foo") == (
        "xkcd: \x02test title\x02 (07 August 2020) | "
        "http://www.xkcd.com/45%0A%20%20%20%20%20%20%20"
    )


def test_search_no_results(mock_requests):
    mock_requests.add(
        "GET",
        "http://www.ohnorobot.com/?s=foo&Search=Search&comic=56&e=0&n=0&b=0&m=0&d=0&t=0",
        json={},
    )

    assert xkcd.xkcd("foo") == "No results found!"
