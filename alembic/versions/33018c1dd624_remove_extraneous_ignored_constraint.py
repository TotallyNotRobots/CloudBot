"""remove extraneous ignored constraint

Revision ID: 33018c1dd624
Revises: 4082d6d3845c
Create Date: 2026-11-21 00:52:42.913942

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "33018c1dd624"
down_revision: str | Sequence[str] | None = "4082d6d3845c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspect = sa.inspect(bind)
    table = sa.table(
        "ignored",
        sa.column("connection", sa.String),
        sa.column("channel", sa.String),
        sa.column("mask", sa.String),
        sa.column("status", sa.Boolean),
    )
    if inspect.has_table(table.name):
        old_ignores = bind.execute(sa.select(table)).mappings().all()

        old_table = f"{table.name}_pre_{revision}"
        op.rename_table(table.name, old_table)
        t = op.create_table(
            table.name,
            sa.Column("connection", sa.String, primary_key=True),
            sa.Column("channel", sa.String, primary_key=True),
            sa.Column("mask", sa.String, primary_key=True),
            sa.Column("status", sa.Boolean),
        )
        op.bulk_insert(t, [dict(row) for row in old_ignores])
        op.drop_table(old_table)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspect = sa.inspect(bind)
    table = sa.table(
        "ignored",
        sa.column("connection", sa.String),
        sa.column("channel", sa.String),
        sa.column("mask", sa.String),
        sa.column("status", sa.Boolean),
    )
    if inspect.has_table(table.name):
        old_ignores = bind.execute(sa.select(table)).mappings().all()

        old_table = f"{table.name}_pre_{revision}_downgrade"
        op.rename_table(table.name, old_table)
        t = op.create_table(
            table.name,
            sa.Column("connection", sa.String, primary_key=True),
            sa.Column("channel", sa.String, primary_key=True),
            sa.Column("mask", sa.String, primary_key=True),
            sa.Column("status", sa.Boolean),
            sa.UniqueConstraint("connection", "channel", "mask", "status"),
        )
        op.bulk_insert(t, [dict(row) for row in old_ignores])
        op.drop_table(old_table)
