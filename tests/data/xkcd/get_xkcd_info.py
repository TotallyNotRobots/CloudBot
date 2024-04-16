# pragma: no cover
import json
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent


def get_data(num):
    file = SCRIPT_DIR / f"{num}.json"
    if file.exists():
        with file.open(encoding="utf-8") as f:
            return json.load(f)

    url = f"https://xkcd.com/{num}/info.0.json"

    with requests.get(url) as r:
        if r.status_code == 404:
            return None

        r.raise_for_status()
        return r.json()


def save(i):
    data = get_data(i)
    if data is None:
        return False

    with (SCRIPT_DIR / "{}.json".format(data["num"])).open(
        "w", encoding="utf-8"
    ) as f:
        json.dump(data, f, indent=4)
        f.write("\n")

    return True


def main():
    ids = [1, 10, 20, 50, 100, 500, 1000, 1500, 2000]
    for num in ids:
        save(num)


if __name__ == "__main__":
    main()
