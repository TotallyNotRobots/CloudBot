"""Remove unused status column in ignored table

Revision ID: 524103ded692
Revises: 33018c1dd624
Create Date: 2026-11-24 07:15:27.763609

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "524103ded692"
down_revision: str | Sequence[str] | None = "33018c1dd624"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    if sa.inspect(op.get_bind()).has_table("ignored"):
        with op.batch_alter_table("ignored") as batch:
            batch.drop_column("status")


def downgrade() -> None:
    """Downgrade schema."""
    if sa.inspect(op.get_bind()).has_table("ignored"):
        with op.batch_alter_table("ignored") as batch:
            batch.add_column(
                sa.Column(
                    "status", sa.BOOLEAN(), autoincrement=False, nullable=True
                )
            )
