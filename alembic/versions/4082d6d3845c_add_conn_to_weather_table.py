"""Add conn to weather table

Revision ID: 4082d6d3845c
Revises: 616fa007dc63
Create Date: 2026-11-22 23:01:10.080555

"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

from cloudbot.bot import bot_instance

if TYPE_CHECKING:
    from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "4082d6d3845c"
down_revision: str | Sequence[str] | None = "616fa007dc63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    name = "weather"
    old_name = f"weather_pre_{revision}"
    op.rename_table(name, old_name)

    old_table = sa.table(
        old_name, sa.column("nick", sa.String()), sa.column("loc", sa.String())
    )
    new_table = op.create_table(
        name,
        sa.Column("nick", sa.String(), nullable=False, primary_key=True),
        sa.Column("loc", sa.String(), nullable=False),
        sa.Column("conn", sa.String(), nullable=False, primary_key=True),
    )

    op.bulk_insert(
        new_table,
        [
            {"conn": conn, "loc": row["loc"], "nick": row["nick"]}
            for row in op.get_bind()
            .execute(sa.select(old_table))
            .mappings()
            .all()
            for conn in bot_instance.get_or_raise()
            .get_connection_configs()
            .keys()
        ],
    )
    op.drop_table(old_table.name)


def downgrade() -> None:
    """Downgrade schema."""
    name = "weather"
    old_name = f"weather_pre_{revision}"
    op.rename_table(name, old_name)

    old_table = sa.table(
        old_name,
        sa.column("nick", sa.String()),
        sa.column("loc", sa.String()),
        sa.column("conn", sa.String()),
    )
    new_table = op.create_table(
        name,
        sa.Column("nick", sa.String(), nullable=False, primary_key=True),
        sa.Column("loc", sa.String(), nullable=False),
    )

    locs: defaultdict[str, list[str]] = defaultdict(list)
    for row in op.get_bind().execute(sa.select(old_table)).mappings().all():
        locs[row["nick"]].append(row["loc"])

    op.bulk_insert(
        new_table,
        [
            {"loc": nick_locs[0], "nick": nick}
            for nick, nick_locs in locs.items()
        ],
    )
    op.drop_table(old_table.name)
