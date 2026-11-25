"""Sync nullables after migration

Revision ID: 7ddf6215d3dd
Revises: e31beb6a9203
Create Date: 2025-11-18 17:42:39.879061

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "7ddf6215d3dd"
down_revision: str | Sequence[str] | None = "e31beb6a9203"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    if sa.inspect(op.get_bind()).has_table("tell_messages"):
        with op.batch_alter_table("tell_messages") as batch:
            batch.alter_column(
                "is_read", existing_type=sa.BOOLEAN(), nullable=False
            )


def downgrade() -> None:
    """Downgrade schema."""
    if sa.inspect(op.get_bind()).has_table("tell_messages"):
        with op.batch_alter_table("tell_messages") as batch:
            batch.alter_column(
                "is_read", existing_type=sa.BOOLEAN(), nullable=True
            )
