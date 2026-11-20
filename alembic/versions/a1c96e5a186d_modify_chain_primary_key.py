"""modify chain primary key

Revision ID: a1c96e5a186d
Revises: 7ddf6215d3dd
Create Date: 2026-11-20 21:54:08.453034

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

from cloudbot.util.database import Session

if TYPE_CHECKING:
    from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "a1c96e5a186d"
down_revision: str | Sequence[str] | None = "7ddf6215d3dd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Can't alter key, have to recreate
    inspector = sa.inspect(op.get_bind())
    old_table = sa.table(
        "chain_commands",
        sa.column("hook", sa.String),
        sa.column("allowed", sa.Boolean),
    )
    if inspector.has_table(old_table.name):
        with Session(bind=op.get_bind()) as session:
            old_commands = (
                session.execute(sa.select(old_table)).mappings().fetchall()
            )

        op.drop_table("chain_commands_v2", if_exists=True)
        new_table = op.create_table(
            "chain_commands_v2",
            sa.Column("hook", sa.String, primary_key=True),
            sa.Column("allowed", sa.Boolean),
        )

        op.bulk_insert(
            new_table,
            [
                {"hook": row["hook"], "allowed": row["allowed"]}
                for row in old_commands
            ],
        )

        op.drop_table(old_table.name)


def downgrade() -> None:
    """Downgrade schema."""
    # Can't alter key, have to recreate
    inspector = sa.inspect(op.get_bind())
    old_table = sa.table(
        "chain_commands_v2",
        sa.column("hook", sa.String),
        sa.column("allowed", sa.Boolean),
    )
    if inspector.has_table(old_table.name):
        with Session(bind=op.get_bind()) as session:
            old_commands = (
                session.execute(sa.select(old_table)).mappings().fetchall()
            )

        op.drop_table("chain_commands", if_exists=True)
        new_table = op.create_table(
            "chain_commands",
            sa.Column("hook", sa.String, primary_key=True),
            sa.Column("allowed", sa.Boolean, primary_key=True),
        )

        op.bulk_insert(
            new_table,
            [
                {"hook": row["hook"], "allowed": row["allowed"]}
                for row in old_commands
            ],
        )

        op.drop_table(old_table.name)
