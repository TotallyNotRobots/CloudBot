from pathlib import Path

import requests
from yarl import URL

BASE_URL = URL("https://www.dogpile.com/search")
SCRIPT_DIR = Path(__file__).resolve().parent


def get_data(query_type):  # pragma: no cover
    params = {"q": "test search"}
    with requests.get(
        str(BASE_URL / query_type),
        params=params,
        verify=False,  # nosec
    ) as response:
        response.raise_for_status()
        return response.content


def write_data(query_tyoe):  # pragma: no cover
    with (SCRIPT_DIR / "dogpile-{}.html".format(query_tyoe)).open(
        "wb", encoding="utf-8"
    ) as file:
        file.write(get_data(query_tyoe))


if __name__ == "__main__":
    write_data("web")
    write_data("images")
