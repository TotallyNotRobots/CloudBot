from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import Float, String, and_, column, select, table

from cloudbot import hook
from cloudbot.util import database, textgen

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from cloudbot.bot import CloudBot


@dataclass
class PluginData:
    hookups: textgen.TemplateConfig | None = None


data = PluginData()
seen_table = table(
    "seen_user",
    column("name", String),
    column("time", Float),
    column("quote", String),
    column("chan", String),
    column("host", String),
)


@hook.on_start()
def load_data(bot: CloudBot) -> None:
    data.hookups = textgen.TemplateConfig.from_json_file(
        bot.data_path / "hookup.json"
    )


@hook.command(autohelp=False)
def hookup(db: Session, chan: str) -> str | None:
    """- matches two users from the channel in a sultry scene."""
    if seen_table.name not in database.metadata.tables or not data.hookups:
        return None

    times = time.time() - 86400
    results = db.execute(
        select(seen_table.c.name)
        .where(and_(seen_table.c.chan == chan, seen_table.c.time > times))
        .order_by(seen_table.c.time)
    ).fetchall()

    if not results or len(results) < 2:
        return "something went wrong"

    # Make sure the list of people is unique
    people: list[str] = sorted({row[0] for row in results})
    random.shuffle(people)
    person1, person2 = people[:2]
    variables = {"user1": person1, "user2": person2}

    return data.hookups.make_generator(
        has_target=False, variables=variables
    ).generate_string()
