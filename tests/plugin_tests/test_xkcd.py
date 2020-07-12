import datetime
import json

import pytest

from plugins import xkcd
from tests.util import test_data_dir

DATA_PATH = test_data_dir / "xkcd"


def get_files():
    for file in DATA_PATH.rglob("*.json"):
        yield int(file.stem)


def load_data(xkcd_id):
    file = DATA_PATH / "{}.json".format(xkcd_id)

    with file.open() as f:
        return json.load(f)


@pytest.mark.parametrize("xkcd_id", list(get_files()))
def test_info(xkcd_id, mock_requests):
    data = load_data(xkcd_id)
    mock_requests.add(
        "GET", "http://www.xkcd.com/{}/info.0.json".format(xkcd_id), json=data,
    )

    date = datetime.date(
        year=int(data["year"]), month=int(data["month"]), day=int(data["day"]),
    )

    no_url = "xkcd: \x02{}\x02 ({:%d %B %Y})".format(data["title"], date)

    with_url = no_url + " | http://www.xkcd.com/{}".format(xkcd_id)

    assert xkcd.xkcd_info(str(xkcd_id)) == no_url
    assert xkcd.xkcd_info(str(xkcd_id), True) == with_url
