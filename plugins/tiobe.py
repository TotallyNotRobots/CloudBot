# Returns the tiobe index ranking for the month
# Author: Matheus Fillipe
# Date: 19/09/2022

import re
from dataclasses import asdict, dataclass
from enum import Enum, auto
from typing import List

import requests
from bs4 import BeautifulSoup, Tag

from cloudbot import hook

BASE_URL = "https://www.tiobe.com"
TABLE_URL = f"{BASE_URL}/tiobe-index/"


def get_float(s: str) -> float:
    """Returns first float number contained in a string."""
    return float(re.search(r"\d+\.\d+", s)[0])


class ChangeDirection(Enum):
    UP = auto()
    DOWN = auto()
    NONE = auto()


@dataclass
class TiobeRow:
    rank: int
    last_month_rank: int
    change_direction: ChangeDirection
    logo_url: str
    language: str
    rating: float
    change: float

    def __str__(self):
        return (
            f"{self.rank}) {self.language} ({self.rating:.2f}) "
            f"{'▲' if self.change_direction == ChangeDirection.UP else '▼' if self.change_direction == ChangeDirection.DOWN else ''} {self.change:.2f}%"
        )


@dataclass
class TiobeRowBuilder:
    rank: Tag
    last_month_rank: Tag
    change_direction: Tag
    logo_url: Tag
    language: Tag
    rating: Tag
    change: Tag

    def build(self) -> TiobeRow:
        self.rank = int(int(self.rank.text.strip()))
        self.last_month_rank = int(self.last_month_rank.text.strip())

        img = self.change_direction.find("img")
        self.change_direction = ChangeDirection.NONE
        if img:
            if "up.png" in img["src"]:
                self.change_direction = ChangeDirection.UP
            elif "down.png" in img["src"]:
                self.change_direction = ChangeDirection.DOWN

        img = self.logo_url.find("img")
        self.logo_url = BASE_URL + img["src"] if img else ""

        self.language = self.language.text.strip()

        self.rating = get_float(self.rating.text)
        self.change = get_float(self.change.text)

        return TiobeRow(**asdict(self))


def get_table() -> List[TiobeRow]:
    """Returns the tiobe index table."""
    r = requests.get(TABLE_URL)
    soup = BeautifulSoup(r.content, "html.parser")
    table = soup.find(
        "table", attrs={"class": "table table-striped table-top20"}
    )
    table2 = soup.find("table", attrs={"id": "otherPL"})
    top20 = [
        TiobeRowBuilder(*(ele for ele in row.find_all("td"))).build()
        for row in table.find("tbody").find_all("tr")
    ]
    elms = [row.find_all("td") for row in table2.find("tbody").find_all("tr")]
    others = []
    for rank, language, rating in elms:
        others.append(
            TiobeRow(
                rank=int(rank.text.strip()),
                last_month_rank=0,
                change_direction=ChangeDirection.NONE,
                logo_url="",
                language=language.text.strip(),
                rating=get_float(rating.text),
                change=0.0,
            )
        )
    return top20 + others


@hook.command("tiobe", "tiobeindex", autohelp=False)
def tiobe(reply, text):
    """Returns the tiobe index ranking for the month."""
    rows = get_table()
    arg = ""
    if text.split():
        arg = text.split()[0]
    # If is digit return the ranking for the language
    if arg.isdigit():
        try:
            for row in rows[int(arg) - 1 : int(arg) + 5]:
                reply(str(row))
        except IndexError:
            reply("Invalid rank position")

    # If is a language return the ranking for the language
    elif arg:
        for i, row in enumerate(rows):
            if arg.casefold() in row.language.casefold():
                reply(str(row))
                return
        else:
            reply("Language not found in the top 50")
            return

    else:
        for row in rows[:5]:
            reply(str(row))
